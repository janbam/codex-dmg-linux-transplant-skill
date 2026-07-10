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
5. Extract the app, icon, plugins, and skills with `../scripts/extract-codex-dmg-assets.py`
6. Bootstrap Electron with the extracted version
7. Install a bundled Linux Codex CLI
8. Rebuild Linux-native modules
9. Write the main install with `../scripts/write-main-install.sh`
10. Patch recognized desktop flags
11. Launch the final wrapper and verify it
12. Remove stale versioned launchers only after verification

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

- wrapper launches from `~/.local/bin/codex-desktop`
- desktop entry displays `ChatGPT`
- icon matches the DMG's `CFBundleIconFile`
- bundled Linux Codex CLI is present
- `app.asar` matches the new build
- native modules are Linux binaries for the target Electron ABI
- plugin and skill trees are present when supplied upstream
- Electron's runtime resource directory links to those plugin and skill trees
- old versioned launchers are gone unless requested
