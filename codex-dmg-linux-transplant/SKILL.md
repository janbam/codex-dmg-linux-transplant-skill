---
name: codex-dmg-linux-transplant
description: Install or update Codex Desktop on Linux from a Codex.dmg when no official Linux build exists. Use when the user wants a clean install or update from a DMG, wants the DMG found in Downloads or elsewhere, or wants the new build installed as the single main Codex desktop version.
---

# Codex DMG → Linux Transplant

Use this skill when Codex Desktop must be installed or updated on Linux from a macOS `Codex.dmg`.

## Non-negotiable rules

1. **Assume no existing Codex desktop install.** Never depend on an older community port.
2. **Probe the machine first.** Read the references and run `scripts/probe-system.sh`.
3. **Install one main version only.** Final paths:
   - `~/.local/opt/codex-desktop`
   - `~/.local/bin/codex-desktop`
   - `~/.local/share/applications/codex-desktop.desktop`
4. **Always install the default Codex icon from the DMG.** Do not use a placeholder or a borrowed icon.
5. **Always provide a Linux Codex CLI path.** Do not rely on a preexisting global `codex` command being present.
6. **Do not finish until the installed wrapper actually launches.** A staged build is not enough.
7. **No side-by-side versioned launchers** unless the user explicitly asks for them.
8. **DMG source order:** user path → safe search → default URL `https://persistent.oaistatic.com/codex-app-prod/Codex.dmg`.

## Required reading order

1. `references/workflow.md`
2. `references/system-checks.md`
3. `references/native-modules.md`
4. `references/install-layout.md`
5. `references/desktop-flags.md`

## Default workflow

### 1) Probe and satisfy prerequisites
Run:

```bash
./scripts/probe-system.sh
./scripts/ensure-prereqs.sh
```

### 2) Locate or fetch the DMG
Use a provided path if available. Otherwise search safely. If nothing is found, use the default Codex DMG URL.

### 3) Extract metadata and assets from the DMG
Run:

```bash
python3 ./scripts/extract-codex-dmg-metadata.py /path/to/Codex.dmg
python3 ./scripts/extract-codex-dmg-assets.py /path/to/Codex.dmg /tmp/codex-stage
```

This must produce at least:
- `resources/app.asar`
- `resources/app.asar.unpacked`
- the default app icon as `icon.png`

### 4) Build a Linux host bundle from scratch
Never assume an older Codex port exists.

Bootstrap Electron:

```bash
./scripts/bootstrap-electron-runtime.sh /tmp/codex-stage <electron-version>
```

Install a Linux Codex CLI into the bundle:

```bash
./scripts/install-codex-cli.sh /tmp/codex-stage
```

Rebuild Linux-native modules:

```bash
./scripts/rebuild-native-modules.sh /tmp/codex-stage <electron-version> <better-sqlite3-version> <node-pty-version>
```

### 5) Install as the main desktop version
Run:

```bash
./scripts/write-main-install.sh /tmp/codex-stage <app-version> <build-number>
```

This now also applies the desktop flag patch automatically.

### 6) Verify the real install
Verification is mandatory:
- `~/.local/bin/codex-desktop` exists and is executable
- the desktop entry exists and points to the main wrapper
- the desktop entry uses the extracted default Codex icon
- the wrapper launches from the final installed path
- no stale `codex-desktop-*` launchers remain unless the user asked to keep them

## Notes

- If launch fails, inspect the actual error and fix the install before finishing.
- If a native module is missing or ABI-mismatched, rebuild it properly for Linux.
- If prerequisite tools are missing, install them first; do not continue with a partial transplant.
