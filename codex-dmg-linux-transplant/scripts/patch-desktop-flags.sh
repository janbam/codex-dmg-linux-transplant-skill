#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo 'usage: patch-desktop-flags.sh <app-dir>' >&2
  exit 1
fi

app_dir="$1"
asar_path="$app_dir/resources/app.asar"
unpacked_dir="$app_dir/resources/app.asar.unpacked"
python_bin="${PYTHON_BIN:-python3}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "missing required Python interpreter: $python_bin" >&2
  exit 1
fi

if [[ ! -f "$asar_path" ]]; then
  echo "missing app.asar: $asar_path" >&2
  exit 1
fi

if [[ ! -d "$unpacked_dir" ]]; then
  echo "missing app.asar.unpacked: $unpacked_dir" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

extract_dir="$tmp_dir/extracted"
mkdir -p "$extract_dir"

# Materialize absent unpacked references once so ASAR extraction does not retry
# hundreds of times for macOS-only files that the Linux transplant never uses.
"$python_bin" - <<'PY' "$asar_path" "$unpacked_dir"
import json
import pathlib
import sys

asar_path = pathlib.Path(sys.argv[1])
unpacked_dir = pathlib.Path(sys.argv[2])
with asar_path.open('rb') as f:
    header_sizes = [int.from_bytes(f.read(4), 'little') for _ in range(4)]
    header = json.loads(f.read(header_sizes[3]))

created = 0

def materialize(node, parts, inherited_unpacked=False):
    global created
    is_unpacked = inherited_unpacked or node.get('unpacked', False)
    files = node.get('files')
    if files is not None:
        for name, child in files.items():
            materialize(child, parts + [name], is_unpacked)
        return

    if not is_unpacked:
        return

    path = unpacked_dir.joinpath(*parts)
    if path.exists():
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    if node.get('executable'):
        path.chmod(path.stat().st_mode | 0o111)
    created += 1

materialize(header, [])
print(f'materialized {created} missing unpacked placeholders')
PY

extract_err="$tmp_dir/extract.err"
attempt=0
while true; do
  rm -rf "$extract_dir"
  mkdir -p "$extract_dir"
  if npx --yes asar extract "$asar_path" "$extract_dir" 2>"$extract_err"; then
    break
  fi

  attempt=$((attempt + 1))
  if (( attempt > 50 )); then
    cat "$extract_err" >&2
    echo 'too many missing unpacked files while extracting app.asar' >&2
    exit 1
  fi

  missing_path="$("$python_bin" - <<'PY' "$extract_err"
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(errors='ignore')
m = re.search(r"ENOENT: .* open '([^']+app\.asar\.unpacked[^']+)'", text)
print(m.group(1) if m else '')
PY
)"

  if [[ -z "$missing_path" ]]; then
    cat "$extract_err" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$missing_path")"
  : > "$missing_path"
  case "$missing_path" in
    */.bin/*|*.sh)
      chmod +x "$missing_path"
      ;;
  esac
done

target_js="$("$python_bin" "$script_dir/desktop_flags.py" --find "$extract_dir")"
if [[ -z "$target_js" ]]; then
  echo 'desktop flag patch skipped: renderer bundle pattern was not found' >&2
  exit 0
fi

if [[ ! -f "$target_js" ]]; then
  echo 'missing renderer bundle with desktop feature flags in extracted app' >&2
  exit 1
fi

pretty_js="$tmp_dir/index.pretty.js"
npx --yes prettier "$target_js" > "$pretty_js"
"$python_bin" "$script_dir/desktop_flags.py" "$pretty_js"

npx --yes prettier "$pretty_js" >/dev/null

install -m 0644 "$pretty_js" "$target_js"

if ! rg -q 'browserPane: enabled' "$target_js"; then
  echo 'desktop flag patch did not apply as expected' >&2
  exit 1
fi

patched_asar="$tmp_dir/app.asar"
unpack_arg=''
if [[ -d "$extract_dir/node_modules" ]]; then
  mapfile -t unpack_dirs < <(find "$extract_dir/node_modules" -mindepth 1 -maxdepth 1 -type d -printf 'node_modules/%f\n' | sort)
  if (( ${#unpack_dirs[@]} > 0 )); then
    unpack_arg="{$(IFS=,; echo "${unpack_dirs[*]}")}"
  fi
fi

if [[ -n "$unpack_arg" ]]; then
  npx --yes asar pack "$extract_dir" "$patched_asar" --unpack-dir "$unpack_arg"
else
  npx --yes asar pack "$extract_dir" "$patched_asar"
fi

# Keep the externalized payload beside the patched archive. The repack step can
# unpack additional dependencies beyond the DMG's original native-module tree.
if [[ -d "${patched_asar}.unpacked" ]]; then
  cp -a "${patched_asar}.unpacked/." "$unpacked_dir/"
fi
install -m 0644 "$patched_asar" "$asar_path"
echo "patched desktop flags in $asar_path"
