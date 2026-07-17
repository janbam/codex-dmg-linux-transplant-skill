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

Install `@openai/codex` into the stage so recovery does not depend on a global command. The wrapper prefers an explicitly configured or user-local `codex`, falls back to the bundled CLI, and exposes `--bundled-codex` to force the bundled binary for comparison or recovery.

## Failure handling

- missing `.node`: identify and rebuild the imported package
- ABI mismatch: rebuild for the exact Electron version
- wrong CLI path: repair the bundled CLI setup
- macOS binary selected: remove it and provide a Linux equivalent or leave the platform-gated feature unavailable

For Electron 42 and newer, the helper adapts older `better-sqlite3` source to V8's mandatory external-pointer tag before rebuilding. Newer `better-sqlite3` releases already include `EXTERNAL_NEW` and `EXTERNAL_VALUE` helper macros; treat those as the upstream fix and do not apply the stale patch shape again.

## If launch still fails

Inspect the real error.

Common outcomes:
- missing `.node` addon: add and rebuild that package
- ABI mismatch: rebuild against the correct Electron version
- wrong CLI path: install or point to a Linux Codex CLI
- wrong runtime path: fix the wrapper to use the bundled Electron runtime

Do not paper over Linux issues by copying mac binaries.
