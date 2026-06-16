# Install Layout

The final install must be the single main Codex Desktop version.

## Fixed target paths

Install to:

```text
~/.local/opt/codex-desktop
~/.local/bin/codex-desktop
~/.local/share/applications/codex-desktop.desktop
~/.local/share/icons/hicolor/512x512/apps/codex-desktop.png
```

## Why fixed paths

Use fixed paths so updates replace the main install instead of creating side-by-side versioned shims.

## Expected app directory

```text
~/.local/opt/codex-desktop/
├── cli/
│   └── node_modules/
├── electron/
│   └── node_modules/electron/
├── package.json
├── icon.png
└── resources/
    ├── app.asar
    └── app.asar.unpacked/
```

## Wrapper requirements

The wrapper should:

- set `ELECTRON_FORCE_IS_PACKAGED=1`
- use an executable `CODEX_CLI_PATH` when one is already set
- prefer the user's local `codex` by default when it is available
- fall back to the bundled Linux Codex CLI if no local CLI is found
- accept `--bundled-codex` to force the bundled CLI for comparison or recovery
- launch the self-contained Electron runtime from the app directory
- pass Wayland flags when appropriate
- avoid `--no-sandbox`; configure `chrome-sandbox` ownership and mode instead

## Desktop entry requirements

The desktop file should:

- point to `~/.local/bin/codex-desktop`
- use the plain app name `Codex`
- use the extracted default Codex icon
- replace older user-local Codex desktop entries after verification

## Cleanup after successful install

After the new install is verified, remove stale items such as:

- `~/.local/bin/codex-desktop-*`
- `~/.local/share/applications/codex-desktop-*.desktop`
- old versioned `~/.local/opt/codex-desktop-*` directories

Only keep alternates if the user explicitly asks.
