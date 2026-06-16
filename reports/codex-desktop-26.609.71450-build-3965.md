# Codex Desktop 26.609.71450 Build 3965

## Result

Codex Desktop `26.609.71450`, build `3965`, was transplanted successfully on
Ubuntu `24.04.4 LTS` x86_64 from the production macOS DMG.

The verified install uses:

- Electron `42.1.0`
- Node module ABI `146`
- local Codex CLI `/home/jan/.nvm/versions/node/v24.13.0/bin/codex`
- local CLI version `0.133.0`
- bundled recovery CLI version `0.140.0`

The desktop app launched from the final wrapper, completed browser login after
the app was restarted, and passed Jan's live smoke test.

## Gremlins Encountered

### Electron Runtime Was Missing After npm Install

This machine intentionally disables npm lifecycle scripts. Installing
`electron@42.1.0` therefore produced the package tree but not the downloaded
Electron runtime payload.

The successful recovery was to run Electron's package installer directly:

```bash
node /tmp/codex-stage/electron/node_modules/electron/install.js
```

The bootstrap script now checks for the actual Electron binary. If it is
missing, the script fails with a narrow opt-in instead of silently bypassing the
npm lifecycle-script safeguard. After reviewing the package-local installer,
rerun only the bootstrap command with:

```bash
CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1 \
  ./codex-dmg-linux-transplant/scripts/bootstrap-electron-runtime.sh \
  /tmp/codex-stage 42.1.0
```

Do not disable the global npm safety gate for this.

### Chromium Sandbox Needed Root Ownership

The first launch failed because Electron's `chrome-sandbox` helper was not
owned and permissioned as Chromium expects. Temporarily adding `--no-sandbox`
proved the rest of the install, but the proper fix was:

```bash
sudo chown root:root ~/.local/opt/codex-desktop/electron/node_modules/electron/dist/chrome-sandbox
sudo chmod 4755 ~/.local/opt/codex-desktop/electron/node_modules/electron/dist/chrome-sandbox
```

Final verified state:

```text
root root 4755 /home/jan/.local/opt/codex-desktop/electron/node_modules/electron/dist/chrome-sandbox
```

The skill now treats `--no-sandbox` as a diagnostic-only escape hatch, not the
shipping configuration.

### `better-sqlite3` Patch Was Stale

The rebuild helper still expected the older `better-sqlite3` source shape that
needed a hand-written Electron 42 V8 external-pointer bridge. The current
install pulled `better-sqlite3 12.11.1`, whose source already contains
`EXTERNAL_NEW` and `EXTERNAL_VALUE` compatibility helpers.

Running the old patch against that source failed before `electron-rebuild`.
The successful path was to skip the obsolete patch and rebuild directly:

```bash
/tmp/codex-stage/native-build/node_modules/.bin/electron-rebuild \
  -f -v 42.1.0 -w better-sqlite3,node-pty \
  --module-dir /tmp/codex-stage/native-build
```

The rebuild script now handles both cases:

- older `better-sqlite3` sources get the Electron 42 helper macros
- newer sources with `EXTERNAL_NEW` and `EXTERNAL_VALUE` are accepted as already
  patched upstream

### Wrapper CLI Policy Needed To Match Development Reality

The first installed wrapper always preferred the bundled CLI. For this Linux
transplant, Jan wanted the desktop app to use the local development `codex` by
default while keeping the bundled CLI available for recovery and comparison.

The wrapper now resolves CLI policy in this order:

1. `--bundled-codex` forces the bundled CLI.
2. An executable `CODEX_CLI_PATH` is honored.
3. `command -v codex` wins by default.
4. Common user-local fallback paths are checked.
5. The bundled CLI is used if no local CLI exists.

This was verified with a wrapper exec stub:

```text
default: CODEX_CLI_PATH=/home/jan/.nvm/versions/node/v24.13.0/bin/codex
--bundled-codex: CODEX_CLI_PATH=/home/jan/.local/opt/codex-desktop/cli/node_modules/.bin/codex
```

### Existing Codex SQLite Backfill Looked Stuck, Then Recovered

Using Jan's real `~/.codex` initially showed a long-running SQLite backfill
state. A clean `CODEX_HOME` proved the transplanted desktop install and
app-server handshake were healthy, so the issue was local state, not the app
bundle.

No destructive action was taken against `~/.codex/sqlite`. Jan restarted the
desktop instance and login worked.

### Browser Plugin Investigation Was Upstream Codex Behavior

The app exposes browser/plugin surfaces, and there is a Codex Chrome extension
that talks to the desktop app. The missing plugin path was not handled as a
Linux transplant blocker. It belongs to Codex's plugin/runtime behavior rather
than the DMG transplant itself.

### Streaming Text Paint Issue Was A Local GPU Debug Setting

The desktop appeared to scroll during streaming while rendering the response
text only after completion. Investigation found plausible rendering suspects
such as Chromium GPU compositing and `content-visibility:auto` in the thread
scroll layout, but Jan identified the actual cause: a local GPU debug option
was enabled. After disabling that option, streaming text displayed correctly.

No app patch was needed for this symptom.

## Verification Receipts

Installed package metadata:

```json
{
  "name": "openai-codex-electron-linux-shim",
  "productName": "Codex",
  "version": "26.609.71450",
  "description": "OpenAI Codex Desktop Linux transplant from DMG",
  "main": "resources/app.asar",
  "codexBuildFlavor": "prod",
  "codexBuildNumber": "3965"
}
```

Native addon proof:

```text
better_sqlite3.node: ELF 64-bit LSB shared object, x86-64, GNU/Linux
pty.node:            ELF 64-bit LSB shared object, x86-64
node-pty.node:       ELF 64-bit LSB shared object, x86-64
```

CLI versions:

```text
/home/jan/.nvm/versions/node/v24.13.0/bin/codex: codex-cli 0.133.0
bundled app CLI:                                      codex-cli 0.140.0
```

Final functional checks:

- wrapper launches from `~/.local/bin/codex-desktop`
- desktop entry points to the wrapper
- app icon is the extracted Codex DMG icon
- app uses the local CLI by default
- bundled CLI remains available with `--bundled-codex`
- sandbox helper is `root root 4755`
- login works
- live smoke test passes

## Skill Updates From This Run

This session produced durable updates to the transplant skill:

- `bootstrap-electron-runtime.sh` now detects blocked Electron runtime downloads
  and requires an explicit narrow opt-in before running Electron's installer.
- `rebuild-native-modules.sh` now accepts newer `better-sqlite3` sources that
  already carry Electron 42 compatibility helpers.
- install documentation now records the local-default CLI policy and
  `--bundled-codex`.
- workflow documentation now records the required `chrome-sandbox` ownership
  and mode instead of relying on `--no-sandbox`.
