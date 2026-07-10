# Install Layout

The final install is one ChatGPT Desktop app at stable Codex-era paths.

## Fixed paths

```text
~/.local/opt/codex-desktop
~/.local/bin/codex-desktop
~/.local/share/applications/codex-desktop.desktop
~/.local/share/icons/hicolor/512x512/apps/codex-desktop.png
```

Do not rename these during an ordinary update. Upstream still uses Codex internally, and retaining the paths updates existing transplants without creating a second app.

## Expected app directory

```text
~/.local/opt/codex-desktop/
├── cli/
├── electron/
├── package.json
├── icon.png
└── resources/
    ├── app.asar
    ├── app.asar.unpacked/
    ├── plugins/              # current unified app
    └── skills/               # current unified app
```

## Wrapper

The wrapper must:

- set `ELECTRON_FORCE_IS_PACKAGED=1`
- prefer the bundled Linux Codex CLI
- optionally fall back to a global `codex`
- launch the bundled Electron runtime
- set `CODEX_ELECTRON_RESOURCES_PATH` to the transplanted resource directory
- expose `plugins/` and `skills/` under Electron's runtime resource directory
- pass Wayland flags when appropriate

## Desktop entry

The desktop file must:

- point to `~/.local/bin/codex-desktop`
- display the name `ChatGPT`
- use the icon extracted from the DMG
- retain `x-scheme-handler/codex`
- replace older user-local Codex desktop entries after verification

## Cleanup

After the new install works, remove stale versioned paths:

- `~/.local/bin/codex-desktop-*`
- `~/.local/share/applications/codex-desktop-*.desktop`
- `~/.local/opt/codex-desktop-*`

Keep alternates only when the user asks.
