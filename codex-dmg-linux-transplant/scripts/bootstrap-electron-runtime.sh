#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: bootstrap-electron-runtime.sh <stage-dir> <electron-version>' >&2
  exit 1
fi

stage_dir="$1"
electron_version="$2"

if ! command -v npm >/dev/null 2>&1; then
  echo 'npm is required' >&2
  exit 1
fi

mkdir -p "$stage_dir/electron"
if [[ ! -f "$stage_dir/electron/package.json" ]]; then
  printf '{"private":true}\n' > "$stage_dir/electron/package.json"
fi

npm install --prefix "$stage_dir/electron" --no-save "electron@${electron_version}"

electron_pkg="$stage_dir/electron/node_modules/electron"
electron_bin="$electron_pkg/dist/electron"

if [[ ! -x "$electron_bin" ]]; then
  echo 'electron runtime payload missing after npm install; running Electron installer once' >&2
  (cd "$electron_pkg" && node install.js)
fi

if [[ ! -x "$electron_bin" ]]; then
  echo 'Electron installer did not produce a runnable payload; downloading Linux runtime directly' >&2
  case "$(uname -m)" in
    x86_64|amd64) electron_arch='x64' ;;
    aarch64|arm64) electron_arch='arm64' ;;
    *)
      echo "unsupported Electron Linux architecture: $(uname -m)" >&2
      exit 1
      ;;
  esac
  if command -v bsdtar >/dev/null 2>&1; then
    extract_zip=(bsdtar -xf)
  elif command -v 7z >/dev/null 2>&1; then
    extract_zip=(7z x -y)
  else
    echo 'bsdtar or 7z is required to extract the Electron runtime fallback' >&2
    exit 1
  fi

  tmp_zip="$(mktemp --suffix=.zip)"
  cleanup_zip() { rm -f "$tmp_zip"; }
  trap cleanup_zip EXIT
  electron_url="https://github.com/electron/electron/releases/download/v${electron_version}/electron-v${electron_version}-linux-${electron_arch}.zip"
  curl -L --fail --retry 3 -o "$tmp_zip" "$electron_url"
  rm -rf "$electron_pkg/dist" "$electron_pkg/path.txt"
  mkdir -p "$electron_pkg/dist"
  if [[ "${extract_zip[0]}" == 'bsdtar' ]]; then
    "${extract_zip[@]}" "$tmp_zip" -C "$electron_pkg/dist"
  else
    "${extract_zip[@]}" "$tmp_zip" "-o$electron_pkg/dist" >/dev/null
  fi
  printf 'electron' > "$electron_pkg/path.txt"
  chmod +x "$electron_bin"
fi

if [[ ! -x "$electron_bin" ]]; then
  echo "failed to install electron runtime payload: $electron_bin" >&2
  exit 1
fi

echo "$electron_bin"
