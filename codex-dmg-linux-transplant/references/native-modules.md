# Native Modules

The DMG supplies portable app code plus macOS-native binaries. Linux needs its own runtime, CLI, and native addons.

## Portable inputs

Carry over:

- `resources/app.asar`
- `resources/app.asar.unpacked` as the dependency skeleton
- `resources/plugins` and `resources/skills` when present
- metadata and the default icon

The unified ChatGPT build stores bundled browser/plugin content outside `app.asar`. Do not omit those directories. The asset extractor removes Mach-O files and macOS app/debug bundles while retaining Linux prebuilds and portable data.

## Never copy as Linux executables

- the bundled macOS `codex`, `rg`, `codex-code-mode-host`, or helper tools
- Mach-O `.node` addons
- `.app` service bundles
- Sparkle or macOS native helpers

## Critical rebuilds

- `better-sqlite3`
- `node-pty`

Use the versions and Electron version reported by `extract-codex-dmg-metadata.py`. For Electron 42 and newer, the helper adapts `better-sqlite3` for V8's mandatory external-pointer tag before rebuilding.

The current unified bundle also contains platform-gated macOS addons and optional device integrations. Do not rebuild them speculatively. If launch or a requested feature reports a missing Linux addon, trace that import and add a real Linux build rather than creating a placeholder.

## CLI

Install `@openai/codex` into the stage and point `CODEX_CLI_PATH` at its Linux binary. A global `codex` is only a fallback.

## Failure handling

- missing `.node`: identify and rebuild the imported package
- ABI mismatch: rebuild for the exact Electron version
- wrong CLI path: repair the bundled CLI setup
- macOS binary selected: remove it and provide a Linux equivalent or leave the platform-gated feature unavailable

Never make a copied macOS binary look successful on Linux.
