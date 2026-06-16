# Workflow

This skill installs or updates Codex Desktop on Linux from `Codex.dmg` without assuming any preexisting Codex desktop app.

## Goal

Produce one main install at:

- `~/.local/opt/codex-desktop`
- `~/.local/bin/codex-desktop`
- `~/.local/share/applications/codex-desktop.desktop`

## Source resolution order

1. User-provided DMG path
2. Safe local search, for example:
   - `~/Downloads`
   - `~/Downloads/00-inbox`
3. Default URL:
   - `https://persistent.oaistatic.com/codex-app-prod/Codex.dmg`

## End-to-end sequence

1. Probe the machine with `../scripts/probe-system.sh`
2. Install missing prerequisites with `../scripts/ensure-prereqs.sh`
3. Resolve the DMG path
4. Extract metadata with `../scripts/extract-codex-dmg-metadata.py`
5. Extract `app.asar`, `app.asar.unpacked`, and the default app icon with `../scripts/extract-codex-dmg-assets.py`
6. Bootstrap a self-contained Electron runtime with `../scripts/bootstrap-electron-runtime.sh`
   - If this reports a missing Electron runtime because lifecycle scripts were blocked, review the warning and rerun the same command with `CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1`.
7. Install a Linux Codex CLI into the bundle with `../scripts/install-codex-cli.sh`
8. Rebuild Linux-native modules with `../scripts/rebuild-native-modules.sh`
9. Write the main install layout with `../scripts/write-main-install.sh`
10. Automatically patch desktop-only renderer flags during install
11. Ensure Chromium's `chrome-sandbox` helper is owned by `root:root` with mode `4755`; ask the human to run the `sudo` commands because Codex does not have root
12. Launch the installed wrapper and verify it works
13. Remove stale versioned launchers and old shims after verification

## Staging layout

```text
/tmp/codex-stage/
├── cli/
│   └── node_modules/
├── electron/
│   └── node_modules/electron/
├── icon.png
└── resources/
    ├── app.asar
    └── app.asar.unpacked/
        └── node_modules/
```

## Verification checklist

- Wrapper launches from `~/.local/bin/codex-desktop`
- Desktop entry points to the wrapper
- Desktop entry uses the extracted default Codex icon
- The install contains a local Linux Codex CLI path
- `resources/app.asar` matches the new DMG build
- `resources/app.asar.unpacked` contains Linux-native modules
- Old versioned launchers are removed unless explicitly requested
- `chrome-sandbox` is configured as `root root 4755`
- login and at least one live smoke test pass from the desktop app
