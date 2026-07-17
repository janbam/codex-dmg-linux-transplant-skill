#!/usr/bin/env bash
set -euo pipefail

echo '== os-release =='
if [[ -f /etc/os-release ]]; then
  cat /etc/os-release
else
  echo '/etc/os-release not found'
fi

echo
echo '== uname =='
uname -a

echo
echo '== package-managers =='
for cmd in pacman paru yay apt apt-get dnf zypper apk emerge; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'found %s -> %s\n' "$cmd" "$(command -v "$cmd")"
  fi
done

echo
echo '== core-tools =='
for cmd in python3 node npm git curl 7z bsdtar gcc g++ make; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'ok %s -> %s\n' "$cmd" "$(command -v "$cmd")"
  else
    printf 'missing %s\n' "$cmd"
  fi
done

echo
echo '== python-packaging =='
python3 - <<'PY'
import importlib.util, ensurepip
print('pip_module', importlib.util.find_spec('pip') is not None)
print('ensurepip', ensurepip is not None)
PY

echo
echo '== electron =='
for cmd in electron electron40 electron41; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'found %s -> %s\n' "$cmd" "$(command -v "$cmd")"
  fi
done

echo
echo '== codex-cli =='
for cmd in codex codex-desktop chatgpt-desktop; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf 'found %s -> %s\n' "$cmd" "$(command -v "$cmd")"
  fi
done

echo
echo '== existing-codex-chatgpt-artifacts =='
find "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/opt" /opt /usr/bin \
  \( -iname '*codex*' -o -iname '*chatgpt*' \) 2>/dev/null | sort -u || true
