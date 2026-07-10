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
6. **Bundle a Linux Codex CLI.** Do not copy the macOS CLI or assume a global `codex` exists.
7. **Preserve external `plugins/` and `skills/` resources when present, but remove Mach-O payloads.**
8. **Do not finish until the final wrapper launches.** A staged build is not an install.
9. **No side-by-side versioned launchers** unless the user asks for them.
10. **DMG source order:** user path → safe local search → `https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg`.

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
python ./scripts/extract-codex-dmg-metadata.py /path/to/ChatGPT.dmg
python ./scripts/extract-codex-dmg-assets.py /path/to/ChatGPT.dmg /tmp/codex-stage
```

The scripts discover the top-level `.app` instead of assuming `Codex.app` or `ChatGPT.app`. The stage must contain `app.asar`, `app.asar.unpacked`, the default icon, and any available portable plugin/skill resources.

### 4) Build the Linux host bundle

Use the versions reported by the metadata script:

```bash
./scripts/bootstrap-electron-runtime.sh /tmp/codex-stage <electron-version>
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

- `~/.local/bin/codex-desktop` exists and is executable
- the desktop entry is named ChatGPT and points to the stable wrapper
- the icon came from the DMG
- the bundled Linux Codex CLI is selected
- the wrapper launches from the final path
- no stale versioned launchers remain unless requested

If launch fails, inspect and fix the actual error. Never treat a successful extraction or build as proof that the transplant works.
