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

if ! target_js="$(node - <<'PY' "$extract_dir"
const fs = require('fs');
const path = require('path');

const root = process.argv[2];
const stack = [root];
while (stack.length) {
  const current = stack.pop();
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    const full = path.join(current, entry.name);
    if (entry.isDirectory()) {
      stack.push(full);
      continue;
    }
    if (!entry.isFile() || !entry.name.endsWith('.js')) continue;
    const txt = fs.readFileSync(full, 'utf8');
    if (
      txt.includes('electron-desktop-features-changed') &&
      txt.includes('browserPane')
    ) {
      console.log(full);
      process.exit(0);
    }
  }
}
process.exit(1);
PY
)"; then
  echo 'desktop flag patch skipped: renderer bundle pattern was not found' >&2
  exit 0
fi

if [[ -z "$target_js" || ! -f "$target_js" ]]; then
  echo 'missing renderer bundle with desktop feature flags in extracted app' >&2
  exit 1
fi

pretty_js="$tmp_dir/index.pretty.js"
npx --yes prettier "$target_js" > "$pretty_js"

"$python_bin" - <<'PY' "$pretty_js"
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text()

dispatch_match = re.search(r"([A-Za-z_$][A-Za-z0-9_$]*)\.dispatchMessage\(`electron-desktop-features-changed`,\s*\{", text)
if dispatch_match is None:
    raise SystemExit('failed to locate desktop feature dispatch call')
dispatch_index = dispatch_match.start()
dispatch_object = dispatch_match.group(1)

lines = text.splitlines(keepends=True)
line_offsets = []
offset = 0
for line in lines:
    line_offsets.append(offset)
    offset += len(line)

dispatch_line = None
for idx, start in enumerate(line_offsets):
    end = start + len(lines[idx])
    if start <= dispatch_index < end:
        dispatch_line = idx
        break

if dispatch_line is None:
    raise SystemExit('failed to map desktop feature dispatch call to line')

func_start_line = None
func_name = None
for idx in range(dispatch_line, -1, -1):
    line = lines[idx].strip()
    if line.startswith('function ') and line.endswith('{'):
        prefix = line[len('function '):]
        candidate = prefix.split('(', 1)[0].strip()
        if candidate:
            func_start_line = idx
            func_name = candidate
            break

if func_start_line is None or func_name is None:
    raise SystemExit('failed to locate desktop feature function start')

func_end_line = None
for idx in range(func_start_line + 1, len(lines)):
    stripped = lines[idx].strip()
    if stripped.startswith('function ') and stripped.endswith('{'):
        func_end_line = idx
        break

if func_end_line is None:
    func_end_line = len(lines)

original_region = ''.join(lines[func_start_line:func_end_line])
if '(0, Z.useEffect)' not in original_region or 'browserPane' not in original_region:
    if not re.search(r"\(0,\s*[A-Za-z_$][A-Za-z0-9_$]*\.useEffect\)", original_region):
        raise SystemExit('desktop feature function candidate failed validation')

cache_match = re.search(r"let\s+\w+\s*=\s*\(0,\s*([A-Za-z_$][A-Za-z0-9_$]*)\.c\)\(\d+\)", original_region)
effect_match = re.search(r"\(0,\s*([A-Za-z_$][A-Za-z0-9_$]*)\.useEffect\)", original_region)
if cache_match is None or effect_match is None:
    raise SystemExit('failed to identify React compiler helpers in desktop feature function')
cache_object = cache_match.group(1)
effect_object = effect_match.group(1)

feature_order = [
    'avatarOverlay',
    'ambientSuggestions',
    'artifactsPane',
    'browserAgent',
    'browserAgentAvailable',
    'browserPane',
    'computerUse',
    'control',
    'multiWindow',
    'projectlessThreads',
]
active_features = [name for name in feature_order if name in original_region]
if 'browserPane' not in active_features:
    raise SystemExit('desktop feature function is missing browserPane')

feature_lines = '\n'.join(f'            {name}: t,' for name in active_features)
dispatch_block = f"""function __FORCED_DESKTOP_FLAGS__() {{
  let e = (0, {cache_object}.c)(4),
    t = !0,
    n,
    r;
  return (
    e[0] !== t
      ? ((n = () => {{
          {dispatch_object}.dispatchMessage(`electron-desktop-features-changed`, {{
{feature_lines}
          }});
        }}),
        (r = [t]),
        (e[0] = t),
        (e[1] = n),
        (e[2] = r))
      : ((n = e[1]), (r = e[2])),
    (0, {effect_object}.useEffect)(n, r),
    null
  );
}}"""

replacement = dispatch_block.replace('__FORCED_DESKTOP_FLAGS__', func_name)
text = ''.join(lines[:func_start_line]) + replacement + '\n' + ''.join(lines[func_end_line:])

for old in [
    'xu(bI)',
    'xu(`2679188970`)',
    'xu(`2425897452`)',
    'xu(`3903742690`)',
    'xu(`4250630194`)',
    'xu(`459748632`)',
    'xu(`2251025435`)',
    'hf(`2679188970`)',
    'hf(`2425897452`)',
    'hf(`3903742690`)',
    'hf(`410262010`)',
    'hf(`1506311413`)',
    'hf(`2171042036`)',
    'hf(`459748632`)',
    'hf(`2251025435`)',
    'Zf(`2679188970`)',
    'Zf(`2425897452`)',
    'Zf(`3903742690`)',
    'Zf(`1506311413`)',
    'Zf(`2171042036`)',
    'Zf(`459748632`)',
    'ms(`2679188970`)',
    'ms(`2425897452`)',
    'ms(`3903742690`)',
    'ms(`1506311413`)',
    'ms(`2171042036`)',
    'ms(`459748632`)',
    'ms(`2212532336`)',
    'Yp()',
]:
    text = text.replace(old, '!0')

path.write_text(text)
PY

npx --yes prettier "$pretty_js" >/dev/null

install -m 0644 "$pretty_js" "$target_js"

if ! rg -q 'browserPane: t' "$target_js"; then
  echo 'desktop flag patch did not apply as expected' >&2
  exit 1
fi

if rg -q 'hf\(`2679188970`\)|hf\(`2425897452`\)|hf\(`3903742690`\)|hf\(`410262010`\)|hf\(`1506311413`\)|hf\(`2171042036`\)|hf\(`459748632`\)|hf\(`2251025435`\)|xu\(`2679188970`\)|xu\(`2425897452`\)|xu\(`3903742690`\)|xu\(`4250630194`\)|xu\(`459748632`\)|xu\(`2251025435`\)|xu\(bI\)|Zf\(`2679188970`\)|Zf\(`2425897452`\)|Zf\(`3903742690`\)|Zf\(`1506311413`\)|Zf\(`2171042036`\)|Zf\(`459748632`\)|ms\(`2679188970`\)|ms\(`2425897452`\)|ms\(`3903742690`\)|ms\(`1506311413`\)|ms\(`2171042036`\)|ms\(`459748632`\)|ms\(`2212532336`\)|\bYp\(\)' "$target_js"; then
  echo 'desktop flag gate calls still remain after patch' >&2
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

if [[ -d "${patched_asar}.unpacked" ]]; then
  cp -a "${patched_asar}.unpacked/." "$unpacked_dir/"
fi

install -m 0644 "$patched_asar" "$asar_path"
echo "patched desktop flags in $asar_path"
