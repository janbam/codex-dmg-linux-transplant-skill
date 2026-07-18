#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo 'usage: write-main-install.sh <stage-dir> <app-version> <build-number>' >&2
  exit 1
fi

stage_dir="$1"
app_version="$2"
build_number="$3"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
final_dir="$HOME/.local/opt/codex-desktop"
wrapper_path="$HOME/.local/bin/codex-desktop"
applications_dir="$HOME/.local/share/applications"
desktop_id="codex-desktop.desktop"
desktop_path="$applications_dir/$desktop_id"
icon_path="$HOME/.local/share/icons/hicolor/512x512/apps/codex-desktop.png"
backup_dir="${final_dir}.backup.$(date +%s)"

# Refuse a partial install when the desktop environment cannot publish the codex:// handler.
for desktop_tool in xdg-mime update-desktop-database; do
  if ! command -v "$desktop_tool" >/dev/null 2>&1; then
    echo "$desktop_tool is required to register the codex:// desktop handler" >&2
    exit 1
  fi
done

mkdir -p "$HOME/.local/opt" "$HOME/.local/bin" "$applications_dir" "$(dirname "$icon_path")"

if [[ ! -f "$stage_dir/resources/app.asar" ]]; then
  echo 'stage_dir is missing resources/app.asar' >&2
  exit 1
fi

if [[ ! -f "$stage_dir/cli/node_modules/.bin/codex" || ! -x "$stage_dir/cli/node_modules/.bin/codex" ]]; then
  echo 'stage_dir is missing a local Linux codex cli' >&2
  exit 1
fi

if [[ ! -f "$stage_dir/icon.png" ]]; then
  echo 'stage_dir is missing icon.png extracted from the dmg' >&2
  exit 1
fi

rm -rf "$stage_dir/native-build" "$stage_dir/.python-deps"

# Swap the validated stage into the stable path while retaining the previous install for rollback.
if [[ -d "$final_dir" ]]; then
  mv "$final_dir" "$backup_dir"
fi
mv "$stage_dir" "$final_dir"

# Expose portable external resources where the transplanted Electron runtime expects them.
runtime_resources="$final_dir/electron/node_modules/electron/dist/resources"
mkdir -p "$runtime_resources"
for resource_name in plugins skills; do
  if [[ -d "$final_dir/resources/$resource_name" ]]; then
    rm -rf "${runtime_resources:?}/$resource_name"
    ln -s "$final_dir/resources/$resource_name" "$runtime_resources/$resource_name"
  fi
done

# Patch before publishing launchers, and preserve both the stage and previous install on failure.
if ! "$script_dir/patch-desktop-flags.sh" "$final_dir"; then
  mv "$final_dir" "$stage_dir"
  if [[ -d "$backup_dir" ]]; then
    mv "$backup_dir" "$final_dir"
  fi
  echo 'desktop flag patch failed; restored the previous install' >&2
  exit 1
fi

install -Dm644 "$final_dir/icon.png" "$icon_path"

cat > "$final_dir/package.json" <<EOF
{
  "name": "openai-codex-electron-linux-shim",
  "productName": "ChatGPT",
  "version": "${app_version}",
  "description": "OpenAI ChatGPT Desktop Linux transplant from DMG",
  "main": "resources/app.asar",
  "codexBuildFlavor": "prod",
  "codexBuildNumber": "${build_number}"
}
EOF

cat > "$wrapper_path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export ELECTRON_FORCE_IS_PACKAGED=1
export BUILD_FLAVOR="${BUILD_FLAVOR:-prod}"
export CODEX_BUILD_NUMBER="${CODEX_BUILD_NUMBER:-__CODEX_BUILD_NUMBER__}"
export CODEX_ELECTRON_RESOURCES_PATH="$HOME/.local/opt/codex-desktop/resources"

bundled_cli="$HOME/.local/opt/codex-desktop/cli/node_modules/.bin/codex"
fork_cli="$HOME/.local/bin/codex-fork"
use_fork=false
app_args=()

# Consume wrapper-only CLI selection before forwarding the remaining arguments to Electron.
for arg in "$@"; do
  case "$arg" in
    --bundled-codex)
      echo '--bundled-codex is no longer supported because bundled Codex is the default' >&2
      exit 2
      ;;
    --use-fork)
      use_fork=true
      ;;
    *)
      app_args+=("$arg")
      ;;
  esac
done
set -- "${app_args[@]}"

# Select exactly one known CLI so inherited environment state cannot change desktop behavior.
if [[ "$use_fork" == true ]]; then
  selected_cli="$fork_cli"
else
  selected_cli="$bundled_cli"
fi
if [[ ! -f "$selected_cli" || ! -x "$selected_cli" ]]; then
  if [[ "$use_fork" == true ]]; then
    echo "--use-fork requires an executable Codex fork at $selected_cli" >&2
  else
    echo "bundled Codex CLI is missing or not executable: $selected_cli" >&2
  fi
  exit 1
fi
export CODEX_CLI_PATH="$selected_cli"

extra_flags=()
if [[ -n "${WAYLAND_DISPLAY-}" || "${XDG_SESSION_TYPE-}" == "wayland" ]]; then
  extra_flags+=(--enable-features=UseOzonePlatform --ozone-platform=wayland --ozone-platform-hint=wayland)
else
  extra_flags+=(--ozone-platform-hint=auto)
fi

exec "$HOME/.local/opt/codex-desktop/electron/node_modules/electron/dist/electron" "${extra_flags[@]}" "$HOME/.local/opt/codex-desktop/resources/app.asar" "$@"
EOF
python3 - <<'PY' "$wrapper_path" "$build_number"
from pathlib import Path
import sys

path = Path(sys.argv[1])
build_number = sys.argv[2]
path.write_text(path.read_text().replace('__CODEX_BUILD_NUMBER__', build_number))
PY
chmod +x "$wrapper_path"

cat > "$desktop_path" <<EOF
[Desktop Entry]
Type=Application
Name=ChatGPT
Comment=ChatGPT Desktop with Codex
Exec=${wrapper_path} %U
Terminal=false
Categories=Development;
Icon=${icon_path}
StartupWMClass=ChatGPT
MimeType=x-scheme-handler/codex;
EOF

# Commit the installed app layout independently from desktop registration, which is safe to retry in place.
handler_error=""
if ! update-desktop-database "$applications_dir"; then
  handler_error="update-desktop-database failed"
elif ! xdg-mime default "$desktop_id" x-scheme-handler/codex; then
  handler_error="xdg-mime could not assign the default handler"
else
  registered_handler="$(xdg-mime query default x-scheme-handler/codex || true)"
  if [[ "$registered_handler" != "$desktop_id" ]]; then
    handler_error="xdg-mime reported ${registered_handler:-no default handler}"
  fi
fi

# Preserve the installed app layout and its backup when only the repairable association failed.
if [[ -n "$handler_error" ]]; then
  echo "installed the app, but failed to register the codex:// handler: $handler_error" >&2
  echo 'run the handler-only repair in references/install-layout.md, then retry from ChatGPT Web' >&2
  if [[ -d "$backup_dir" ]]; then
    echo "previous install backup preserved at $backup_dir" >&2
  fi
  exit 1
fi

# Remove stale desktop entries and immediately rebuild the cache so it describes surviving files.
find "$applications_dir" -maxdepth 1 -type f -name 'codex-desktop-*.desktop' -delete
if ! update-desktop-database "$applications_dir"; then
  echo 'installed the app and handler, but failed to refresh the desktop database after stale-entry cleanup' >&2
  echo 'run the handler-only repair in references/install-layout.md, then retry from ChatGPT Web' >&2
  if [[ -d "$backup_dir" ]]; then
    echo "previous install backup preserved at $backup_dir" >&2
  fi
  exit 1
fi

# Remove stale executable and app alternates only after desktop discovery reaches its final state.
find "$HOME/.local/bin" -maxdepth 1 -type f -name 'codex-desktop-*' -delete
find "$HOME/.local/opt" -maxdepth 1 -mindepth 1 -type d -name 'codex-desktop-*' -exec rm -rf {} +

echo "installed to $final_dir"
if [[ -d "$backup_dir" ]]; then
  echo "backup saved to $backup_dir"
fi
