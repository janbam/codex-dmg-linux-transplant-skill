#!/usr/bin/env bash
set -euo pipefail

missing=()
# Treat desktop handler publication as a core install capability, not a best-effort postflight.
for cmd in python3 node npm git curl 7z gcc g++ make xdg-mime update-desktop-database; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done

if [[ ${#missing[@]} -eq 0 ]]; then
  echo 'all core prerequisites already installed'
  exit 0
fi

# Keep root-owned package installation at the human boundary instead of invoking sudo from Codex.
echo "missing prerequisites: ${missing[*]}" >&2
echo 'ask the system administrator to install the missing commands, then rerun this check' >&2
exit 1
