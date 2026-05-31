#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo 'usage: rebuild-native-modules.sh <stage-dir> <electron-version> <better-sqlite3-version> <node-pty-version>' >&2
  exit 1
fi

stage_dir="$1"
electron_version="$2"
better_sqlite3_version="$3"
node_pty_version="$4"
build_dir="$stage_dir/native-build"

for cmd in npm node python3 gcc g++ make; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "missing required tool: $cmd" >&2
    exit 1
  fi
done

rm -rf "$build_dir"
mkdir -p "$build_dir" "$stage_dir/resources/app.asar.unpacked/node_modules"
printf '{"private":true}\n' > "$build_dir/package.json"

npm install --prefix "$build_dir" --no-save @electron/rebuild \
  "better-sqlite3@${better_sqlite3_version}" \
  "node-pty@${node_pty_version}"

# Bridge better-sqlite3 across Electron 42's mandatory V8 external-pointer tag.
python3 - <<'PY' "$build_dir/node_modules/better-sqlite3"
from pathlib import Path
import sys

module_dir = Path(sys.argv[1])


def replace_once_or_verify(path, old, new):
    text = path.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'failed to patch unexpected better-sqlite3 source: {path}')
    path.write_text(text.replace(old, new, 1))


replace_once_or_verify(
    module_dir / 'src/util/macros.cpp',
    '#define OnlyAddon static_cast<Addon*>(info.Data().As<v8::External>()->Value())',
    '''#if defined(NODE_MODULE_VERSION) && NODE_MODULE_VERSION >= 146
// Preserve the addon pointer behind Electron 42's mandatory V8 sandbox tag.
#define OnlyAddon static_cast<Addon*>(info.Data().As<v8::External>()->Value(v8::kExternalPointerTypeTagDefault))
#else
#define OnlyAddon static_cast<Addon*>(info.Data().As<v8::External>()->Value())
#endif''',
)
replace_once_or_verify(
    module_dir / 'src/util/helpers.cpp',
    '''\t\tfunc,
\t\t0,
\t\tdata''',
    '''\t\tfunc,
\t\tnullptr,
\t\tdata''',
)
replace_once_or_verify(
    module_dir / 'src/better_sqlite3.cpp',
    '\tv8::Local<v8::External> data = v8::External::New(isolate, addon);',
    '''\t#if defined(NODE_MODULE_VERSION) && NODE_MODULE_VERSION >= 146
\t// Preserve the addon pointer behind Electron 42's mandatory V8 sandbox tag.
\tv8::Local<v8::External> data = v8::External::New(isolate, addon, v8::kExternalPointerTypeTagDefault);
\t#else
\tv8::Local<v8::External> data = v8::External::New(isolate, addon);
\t#endif''',
)
PY

"$build_dir/node_modules/.bin/electron-rebuild" -f -v "$electron_version" -w better-sqlite3,node-pty --module-dir "$build_dir"

rm -rf "$stage_dir/resources/app.asar.unpacked/node_modules/better-sqlite3"
rm -rf "$stage_dir/resources/app.asar.unpacked/node_modules/node-pty"
cp -a "$build_dir/node_modules/better-sqlite3" "$stage_dir/resources/app.asar.unpacked/node_modules/"
cp -a "$build_dir/node_modules/node-pty" "$stage_dir/resources/app.asar.unpacked/node_modules/"

echo 'rebuilt native modules into app.asar.unpacked'
