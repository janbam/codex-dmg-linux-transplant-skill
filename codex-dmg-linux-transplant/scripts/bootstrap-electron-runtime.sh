#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bootstrap-electron-runtime.sh <stage-dir> <electron-version>' >&2
  exit 1
fi

stage_dir="$1"
electron_version="$2"

for cmd in npm node; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required" >&2
    exit 1
  fi
done

mkdir -p "$stage_dir/electron"
if [[ ! -f "$stage_dir/electron/package.json" ]]; then
  printf '{"private":true}\n' > "$stage_dir/electron/package.json"
fi

npm install --prefix "$stage_dir/electron" --no-save "electron@${electron_version}"

electron_bin="$stage_dir/electron/node_modules/electron/dist/electron"
electron_install_js="$stage_dir/electron/node_modules/electron/install.js"

# Recover the runtime payload only after an explicit narrow opt-in.
if [[ ! -x "$electron_bin" ]]; then
  if [[ ! -f "$electron_install_js" ]]; then
    echo "electron install.js is missing: $electron_install_js" >&2
    exit 1
  fi
  if [[ "${CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS-}" != "1" ]]; then
    echo "electron runtime is missing because npm lifecycle scripts likely did not run: $electron_bin" >&2
    echo "after reviewing this narrow dependency-supplied installer, rerun with:" >&2
    echo "  CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1 $0 $stage_dir $electron_version" >&2
    exit 1
  fi
  node "$electron_install_js"
fi

if [[ ! -x "$electron_bin" ]]; then
  echo "electron runtime was not installed: $electron_bin" >&2
  exit 1
fi

echo "$electron_bin"
