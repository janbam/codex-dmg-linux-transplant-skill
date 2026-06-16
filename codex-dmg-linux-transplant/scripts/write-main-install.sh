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
desktop_path="$HOME/.local/share/applications/codex-desktop.desktop"
icon_path="$HOME/.local/share/icons/hicolor/512x512/apps/codex-desktop.png"
backup_dir="${final_dir}.backup.$(date +%s)"

mkdir -p "$HOME/.local/opt" "$HOME/.local/bin" "$HOME/.local/share/applications" "$(dirname "$icon_path")"

if [[ ! -f "$stage_dir/resources/app.asar" ]]; then
  echo 'stage_dir is missing resources/app.asar' >&2
  exit 1
fi

if [[ ! -x "$stage_dir/cli/node_modules/.bin/codex" ]]; then
  echo 'stage_dir is missing a local Linux codex cli' >&2
  exit 1
fi

if [[ ! -f "$stage_dir/icon.png" ]]; then
  echo 'stage_dir is missing icon.png extracted from the dmg' >&2
  exit 1
fi

rm -rf "$stage_dir/native-build" "$stage_dir/.python-deps"

if [[ -d "$final_dir" ]]; then
  mv "$final_dir" "$backup_dir"
fi
mv "$stage_dir" "$final_dir"
install -Dm644 "$final_dir/icon.png" "$icon_path"

cat > "$final_dir/package.json" <<EOF
{
  "name": "openai-codex-electron-linux-shim",
  "productName": "Codex",
  "version": "${app_version}",
  "description": "OpenAI Codex Desktop Linux transplant from DMG",
  "main": "resources/app.asar",
  "codexBuildFlavor": "prod",
  "codexBuildNumber": "${build_number}"
}
EOF

cat > "$wrapper_path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

export ELECTRON_FORCE_IS_PACKAGED=1

bundled_cli="$HOME/.local/opt/codex-desktop/cli/node_modules/.bin/codex"
use_bundled_cli=false
app_args=()
for arg in "$@"; do
  case "$arg" in
    --bundled-codex)
      use_bundled_cli=true
      ;;
    *)
      app_args+=("$arg")
      ;;
  esac
done
set -- "${app_args[@]}"

# Resolve the Codex CLI policy before Electron starts so the app-server child uses the intended binary.
if [[ "$use_bundled_cli" == true ]]; then
  export CODEX_CLI_PATH="$bundled_cli"
elif [[ -n "${CODEX_CLI_PATH-}" && -x "$CODEX_CLI_PATH" ]]; then
  export CODEX_CLI_PATH
elif command -v codex >/dev/null 2>&1; then
  export CODEX_CLI_PATH="$(command -v codex)"
else
  for candidate in "$HOME"/.nvm/versions/node/*/bin/codex "$HOME/.local/bin/codex"; do
    if [[ -x "$candidate" ]]; then
      export CODEX_CLI_PATH="$candidate"
      break
    fi
  done
  if [[ -z "${CODEX_CLI_PATH-}" && -x "$bundled_cli" ]]; then
    export CODEX_CLI_PATH="$bundled_cli"
  fi
fi

extra_flags=()
if [[ -n "${WAYLAND_DISPLAY-}" || "${XDG_SESSION_TYPE-}" == "wayland" ]]; then
  extra_flags+=(--enable-features=UseOzonePlatform --ozone-platform=wayland --ozone-platform-hint=wayland)
else
  extra_flags+=(--ozone-platform-hint=auto)
fi

exec "$HOME/.local/opt/codex-desktop/electron/node_modules/electron/dist/electron" "${extra_flags[@]}" "$HOME/.local/opt/codex-desktop/resources/app.asar" "$@"
EOF
chmod +x "$wrapper_path"

cat > "$desktop_path" <<EOF
[Desktop Entry]
Type=Application
Name=Codex
Comment=OpenAI Codex Desktop
Exec=${wrapper_path} %U
Terminal=false
Categories=Development;
Icon=${icon_path}
StartupWMClass=Codex
MimeType=x-scheme-handler/codex;
EOF

"$script_dir/patch-desktop-flags.sh" "$final_dir"

find "$HOME/.local/bin" -maxdepth 1 -type f -name 'codex-desktop-*' -delete
find "$HOME/.local/share/applications" -maxdepth 1 -type f -name 'codex-desktop-*.desktop' -delete
find "$HOME/.local/opt" -maxdepth 1 -mindepth 1 -type d -name 'codex-desktop-*' -exec rm -rf {} +

echo "installed to $final_dir"
if [[ -d "$backup_dir" ]]; then
  echo "backup saved to $backup_dir"
fi
