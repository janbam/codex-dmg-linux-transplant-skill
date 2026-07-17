---
name: codex-dmg-linux-transplant
description: "Install or update the ChatGPT desktop app on Linux from ChatGPT.dmg (formerly Codex.dmg) when no official Linux build exists. Use for fresh installs, DMG updates, Codex-to-ChatGPT migration, or replacing an existing transplanted desktop build with the current release."
---

# ChatGPT/Codex DMG → Linux Transplant

Transplant the macOS ChatGPT desktop app—the renamed Codex app—onto Linux. The visible app is now ChatGPT; its bundle ID, `codex://` URL scheme, CLI, and much of its package metadata still use Codex.

## Non-negotiable rules

1. **Assume no existing desktop install.** Never depend on an older community port.
2. **Probe first.** Read the references and run `scripts/probe-system.sh`.
3. **Keep one main install at the stable compatibility paths:**
   - `~/.local/opt/codex-desktop`
   - `~/.local/bin/codex-desktop`
   - `~/.local/share/applications/codex-desktop.desktop`
4. **Brand the installed desktop entry as ChatGPT.** Keep the Codex paths and `codex://` handler because upstream still uses them internally.
5. **Use the default icon named by the DMG's `Info.plist`.** Never substitute a placeholder.
6. **Bundle a Linux Codex CLI.** Never copy the macOS CLI or depend on a global `codex` being present.
7. **Preserve external `plugins/` and `skills/` resources when present, but remove Mach-O payloads.**
8. **Do not finish until the final wrapper launches.** A staged build is not an install.
9. **No side-by-side versioned launchers** unless the user asks for them.
10. **DMG source order:** user path → safe local search → `https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg`.
11. **Do not bypass Chromium sandboxing.** If `chrome-sandbox` needs root ownership, ask the human to run the required `sudo chown` and `sudo chmod 4755` commands.

## Required reading order

1. `references/workflow.md`
2. `references/system-checks.md`
3. `references/native-modules.md`
4. `references/install-layout.md`
5. `references/desktop-flags.md`

## Workflow

### 1) Probe and satisfy prerequisites

```bash
./scripts/probe-system.sh
./scripts/ensure-prereqs.sh
```

### 2) Resolve the DMG

Use a provided path first. Search likely download folders next. Otherwise fetch the default `ChatGPT.dmg` URL. Use the first item in `appcast.xml` when the user asks you to confirm the latest release.

### 3) Extract metadata and assets

```bash
python3 ./scripts/extract-codex-dmg-metadata.py /path/to/ChatGPT.dmg
python3 ./scripts/extract-codex-dmg-assets.py /path/to/ChatGPT.dmg /tmp/codex-stage
```

The scripts discover the top-level `.app` instead of assuming `Codex.app` or `ChatGPT.app`. The stage must contain `resources/app.asar`, `resources/app.asar.unpacked`, the default icon as `icon.png`, and any available portable plugin/skill resources.

### 4) Build the Linux host bundle

Use the versions reported by the metadata script:

```bash
./scripts/bootstrap-electron-runtime.sh /tmp/codex-stage <electron-version>
```

If npm lifecycle-script hardening leaves the Electron runtime binary missing,
review the script's warning and rerun only that bootstrap command with
`CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1`. This opt-in executes Electron's
package-local `install.js`; do not disable global npm safeguards.

Install a Linux Codex CLI into the bundle:

```bash
./scripts/install-codex-cli.sh /tmp/codex-stage
./scripts/rebuild-native-modules.sh /tmp/codex-stage <electron-version> <better-sqlite3-version> <node-pty-version>
```

### 5) Install the main version

```bash
./scripts/write-main-install.sh /tmp/codex-stage <app-version> <build-number>
```

This also patches recognized desktop feature flags and writes a ChatGPT-branded desktop entry.

### 6) Verify the final install

Check all of these:

The generated wrapper uses the bundled Linux Codex CLI installed into the app directory by default. Pass `--use-fork` to select `~/.local/bin/codex-fork` for that launch.

Verification is mandatory:

- `~/.local/bin/codex-desktop` exists and is executable
- the desktop entry is named ChatGPT and points to the stable wrapper
- the icon came from the DMG
- the wrapper selects bundled Codex by default and selects `codex-fork` only with `--use-fork`
- the wrapper launches from the final path
- no stale versioned launchers remain unless requested

If launch fails, inspect and fix the actual error. Never treat a successful extraction or build as proof that the transplant works.
