#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo 'usage: install-codex-cli.sh <stage-dir> <codex-version>' >&2
  exit 1
fi

stage_dir="$1"
codex_version="$2"
cli_dir="$stage_dir/cli"
mkdir -p "$cli_dir"

if [[ ! "$codex_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?$ ]]; then
  echo "invalid codex version: $codex_version" >&2
  exit 1
fi

if [[ ! -f "$cli_dir/package.json" ]]; then
  printf '{"private":true}\n' > "$cli_dir/package.json"
fi

empty_user_config="$(mktemp)"
empty_global_config="$(mktemp)"

# Remove the isolated npm configuration on every exit path.
cleanup() {
  rm -f "$empty_user_config" "$empty_global_config"
}
trap cleanup EXIT

# Bypass machine-wide release-age and lifecycle gates only for this exact DMG-selected package version.
npm install --prefix "$cli_dir" --no-save "@openai/codex@$codex_version" \
  --ignore-scripts=false \
  --userconfig "$empty_user_config" \
  --globalconfig "$empty_global_config"

if [[ ! -x "$cli_dir/node_modules/.bin/codex" ]]; then
  echo 'failed to install local codex cli' >&2
  exit 1
fi

installed_version="$("$cli_dir/node_modules/.bin/codex" --version)"
if [[ "$installed_version" != "codex-cli $codex_version" ]]; then
  echo "installed codex version mismatch: expected $codex_version, got $installed_version" >&2
  exit 1
fi

echo "$cli_dir/node_modules/.bin/codex"
