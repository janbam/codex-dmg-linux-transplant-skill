# Workflow

The Codex desktop app was renamed to ChatGPT in July 2026. Upstream changed the DMG and `.app` names, but retained `com.openai.codex`, the `codex://` scheme, the Codex CLI contract, and Codex-oriented package metadata.

## Goal

Produce one ChatGPT-branded install at the stable compatibility paths:

- `~/.local/opt/codex-desktop`
- `~/.local/bin/codex-desktop`
- `~/.local/share/applications/codex-desktop.desktop`

## Confirm the current release

Read the first `<item>` from:

```text
https://persistent.oaistatic.com/codex-app-prod/appcast.xml
```

The feed is the release authority. The static DMG URL is rolling and does not include a version in its filename.

## Source order

1. User-provided `.dmg`
2. Safe local search in `~/Downloads` and `~/Downloads/00-inbox`
3. `https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg`

## End-to-end sequence

1. Run `../scripts/probe-system.sh`
2. Run `../scripts/ensure-prereqs.sh`
3. Resolve the DMG
4. Extract metadata with `../scripts/extract-codex-dmg-metadata.py`
5. Extract the app, default icon, plugins, and skills with `../scripts/extract-codex-dmg-assets.py`
6. Bootstrap a self-contained Electron runtime with `../scripts/bootstrap-electron-runtime.sh`
   - If this reports a missing Electron runtime because lifecycle scripts were blocked, review the warning and rerun the same command with `CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1`.
7. Install the exact `codex_cli_version` reported from the DMG with `../scripts/install-codex-cli.sh <stage-dir> <codex-cli-version>`
   - This one exact install uses isolated npm configuration files so the operator's release-age and lifecycle gates remain intact everywhere else.
8. Rebuild Linux-native modules with `../scripts/rebuild-native-modules.sh`
9. Write the main install layout with `../scripts/write-main-install.sh`
   - The installer patches desktop-only renderer flags.
   - The installer publishes the desktop entry and makes it the default `codex://` handler.
10. Ensure Chromium's `chrome-sandbox` helper is owned by `root:root` with mode `4755`; ask the human to run the `sudo` commands because Codex does not have root
11. Launch the installed wrapper and verify it works
12. Open the desktop app from ChatGPT Web and verify `codex://threads/new` reaches ChatGPT
13. Remove stale versioned launchers and old shims after verification

## Staging layout

```text
/tmp/codex-stage/
├── cli/
├── electron/
├── icon.png
└── resources/
    ├── app.asar
    ├── app.asar.unpacked/
    ├── plugins/              # when present in the DMG
    └── skills/               # when present in the DMG
```

The asset extractor removes `.app`, `.dSYM`, and Mach-O files from copied plugin and skill trees. Keep Linux prebuilds and portable JS/data.

## Verification

- Wrapper launches from `~/.local/bin/codex-desktop`
- `~/.local/bin/codex-desktop --check-update` reports the installed and latest appcast builds without launching Electron
- Desktop entry points to the wrapper
- Desktop entry displays `ChatGPT` and uses the icon named by the DMG
- `xdg-mime query default x-scheme-handler/codex` returns `codex-desktop.desktop`
- `gio mime x-scheme-handler/codex`, when available, lists `codex-desktop.desktop` as registered and default
- ChatGPT Web can open the installed app through `codex://threads/new`
- The wrapper uses bundled Codex by default and selects `~/.local/bin/codex-fork` only with `--use-fork`
- The bundled Linux Codex version matches the macOS Codex version reported from the source DMG
- `resources/app.asar` matches the new DMG build
- `resources/app.asar.unpacked` contains Linux-native modules
- Plugin and skill trees are present when supplied upstream and exposed under Electron's runtime resource directory
- Old versioned launchers are removed unless explicitly requested
- `chrome-sandbox` is configured as `root root 4755`
- Login and at least one live smoke test pass from the desktop app
