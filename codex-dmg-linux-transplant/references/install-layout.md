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
├── check-desktop-update.py
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
- use the bundled Linux Codex CLI by default
- accept `--use-fork` to select `~/.local/bin/codex-fork` for one launch
- consume `--use-fork` instead of forwarding it to Electron
- accept `--check-update` by itself to report the installed and latest Desktop builds without launching Electron
- fail clearly when the selected CLI is missing or not executable
- reject the obsolete `--bundled-codex` selector because bundled Codex is already the default
- launch the self-contained Electron runtime from the app directory
- set `CODEX_ELECTRON_RESOURCES_PATH` to the transplanted resource directory
- expose `plugins/` and `skills/` under Electron's runtime resource directory
- pass Wayland flags when appropriate
- avoid `--no-sandbox`; configure `chrome-sandbox` ownership and mode instead

The installed app metadata records both the Desktop build and the exact bundled Codex CLI version. `codex-desktop --check-update` compares the numerical Desktop build with the first item in OpenAI's Sparkle appcast; it does not use CLI releases as a proxy for Desktop availability.

## Desktop entry

The desktop file must:

- point to `~/.local/bin/codex-desktop`
- display the name `ChatGPT`
- use the icon extracted from the DMG
- retain `x-scheme-handler/codex`
- accept deep-link URLs through the `%U` field code
- be published with `update-desktop-database`
- become the default handler through `xdg-mime`
- replace older user-local Codex desktop entries after verification

Declaring `MimeType=x-scheme-handler/codex;` in the desktop file is not enough. Without refreshing the desktop database and assigning the default handler, GNOME can show “No Apps available” when ChatGPT Web opens `codex://threads/new`.

### Repair an existing handler

When the installed wrapper already works and the desktop entry passes validation, repair the association without rebuilding the transplant:

```bash
desktop-file-validate ~/.local/share/applications/codex-desktop.desktop
update-desktop-database ~/.local/share/applications
xdg-mime default codex-desktop.desktop x-scheme-handler/codex
xdg-mime query default x-scheme-handler/codex
gio mime x-scheme-handler/codex  # when gio is available
```

The XDG query must return `codex-desktop.desktop`. When `gio` is available, its output must list the same desktop entry as registered and default. Finish with a real click on **Open desktop app** in ChatGPT Web; querying configuration alone does not prove browser-to-app delivery.

The installer commits the app layout before registering the scheme. If only registration fails, it preserves that layout and any previous-install backup, exits nonzero, and points to this repair sequence. Repair the association in place, then complete the normal launch and live verification.

## Cleanup

After the new install works, remove stale versioned paths:

- `~/.local/bin/codex-desktop-*`
- `~/.local/share/applications/codex-desktop-*.desktop`
- `~/.local/opt/codex-desktop-*`

Keep alternates only when the user asks.
