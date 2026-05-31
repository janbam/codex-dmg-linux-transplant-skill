# Codex Desktop 26.527.31326 Build 3390

## Result

Codex Desktop `26.527.31326`, build `3390`, was transplanted successfully on
Ubuntu `24.04.4 LTS` x86_64 from the production arm64 macOS DMG.

The verified install uses:

- Electron `42.1.0`
- Node module ABI `146`
- local Codex CLI `/home/jan/src/codex/codex-rs/target/release/codex`
- local CLI version `0.133.0`

The wrapper reached `startup complete`, showed the main window, initialized
SQLite, and completed the app-server handshake with the local forked CLI.

## Gremlins Encountered

### Electron Runtime Was Missing After npm Install

This machine has `npm` lifecycle scripts disabled intentionally. Installing
`electron@42.1.0` therefore created the package tree without downloading the
runtime payload.

The narrow workaround was:

```bash
cd /tmp/codex-stage/electron/node_modules/electron
node install.js
```

Do not disable the global safeguard. Run only Electron's audited installer for
the staged package.

### Chromium Sandbox Needed Root Ownership

A user-local Electron runtime aborts until its sandbox helper has the required
ownership and mode:

```bash
sudo chown root:root ~/.local/opt/codex-desktop/electron/node_modules/electron/dist/chrome-sandbox
sudo chmod 4755 ~/.local/opt/codex-desktop/electron/node_modules/electron/dist/chrome-sandbox
```

Run this after each clean install because copying a new Electron tree resets
the helper to ordinary user ownership.

### The DMG's Unpacked Tree Is Required

Copying only `resources/app.asar` is insufficient. The DMG contains a real
`resources/app.asar.unpacked` tree with required files. Omitting it produced
missing-module failures during startup.

The asset extractor must copy both:

```text
resources/app.asar
resources/app.asar.unpacked
```

### Renderer Repacking Externalized Additional Dependencies

The desktop-flag patch repacks `app.asar`. During that repack, `asar` may move
additional dependencies such as `tslib`, `bindings`, and `file-uri-to-path`
into a generated `app.asar.unpacked` payload.

Installing only the new `app.asar` discarded those dependencies and caused:

```text
Error: Cannot find module 'tslib'
```

Merge the repacker's generated unpacked tree back beside the patched archive.

### Placeholder Extraction Was Quadratic

The old desktop-flag patch discovered one missing unpacked file per extraction
attempt. This DMG referenced hundreds of unpacked files, including macOS-only
`node-hid` sources, and exceeded the retry bound.

Read the ASAR header once and materialize absent unpacked placeholders in one
pass before extraction. Keep the retry loop only as a fail-loud fallback.

### Ubuntu Has `python3`, Not Necessarily `python`

The skill probed `python3` but invoked `python` inside the desktop-flag patch.
On this host that failed with:

```text
python: command not found
```

Use `python3` consistently.

### `better-sqlite3` Needed An Electron 42 Compatibility Bridge

`better-sqlite3 12.10.0` source did not compile against Electron `42.1.0`
because V8 now requires an external-pointer type tag and exposes an ambiguous
null setter overload.

Before `electron-rebuild`, adapt the addon source to:

- pass `v8::kExternalPointerTypeTagDefault` to `v8::External::New`
- pass the same tag to `v8::External::Value`
- pass `nullptr` instead of integer `0` to `SetNativeDataProperty`

The rebuild script now performs this narrowly guarded adaptation and fails
loudly if the expected upstream source shape changes.

## Local CLI Version Skew

The local forked CLI is two minor releases behind upstream. Desktop startup and
the app-server handshake succeeded with `codex-cli 0.133.0`.

One degradation remains: the desktop asks the older CLI to enable experimental
`remote_plugin`, and the CLI rejects that feature as unsupported. Core startup,
account reads, thread listing, model listing, plugin listing, skills listing,
SQLite initialization, and the main window still work.

Treat broader incompatibility from this version skew as a major blocker. Do not
silently substitute npm Codex for the local fork.

## Verification Receipts

Native addon proof inside Electron `42.1.0`:

```json
{"electron":"42.1.0","modules":"146","sqlite":{"answer":42},"pty":"pty-ok"}
```

Final wrapper launch:

```text
stdio_transport_spawned executablePath=.../cli/node_modules/.bin/codex
Current reported app-server version: currentVersion=0.133.0
initialize_handshake_result outcome=success
Codex CLI initialized
local app-server sqlite initialized
startup complete
window ready-to-show
```

The human live smoke test also passed.

