# Native Modules

The DMG gives you portable app code and mac-native binaries. Linux still needs Linux-native dependencies.

## Portable pieces from the DMG

These carry over:

- `resources/app.asar`
- app metadata such as version and build number
- the default app icon

## Non-portable pieces

Do not reuse mac binaries for Linux:

- `.node` addons
- helper executables
- the bundled mac `codex` binary inside the DMG

## Known critical Linux rebuild targets

- `better-sqlite3`
- `node-pty`

## CLI rule

A clean Linux install must not depend on a preexisting global `codex` command.

Install a Linux Codex CLI into the bundle and point `CODEX_CLI_PATH` at it. A global `codex` may be used only as a fallback.

## Rebuild strategy

Use the Electron version extracted from the DMG metadata.

Install the target packages in a staging build directory, then rebuild them specifically for the target Electron version. The helper script uses `electron-rebuild` for this.

For Electron 42 and newer, the helper also adapts `better-sqlite3` source to V8's mandatory external-pointer tag before rebuilding.

## If launch still fails

Inspect the real error.

Common outcomes:
- missing `.node` addon: add and rebuild that package
- ABI mismatch: rebuild against the correct Electron version
- wrong CLI path: install or point to a Linux Codex CLI
- wrong runtime path: fix the wrapper to use the bundled Electron runtime

Do not paper over Linux issues by copying mac binaries.
