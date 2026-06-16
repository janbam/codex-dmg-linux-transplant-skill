# Desktop Flags Patch

This skill now patches the installed app to force-enable desktop-only flags in the renderer after the main install is written.

## Current forced desktop flags

- `avatarOverlay`
- `ambientSuggestions`
- `artifactsPane`
- `browserPane`
- `multiWindow`
- `projectlessThreads`

## Script

Use:

```bash
../scripts/patch-desktop-flags.sh ~/.local/opt/codex-desktop
```

The script extracts `resources/app.asar`, materializes placeholders for missing unpacked dev-only files in one pass, patches the renderer bundle when the current bundle shape is recognized, and repacks `app.asar` while preserving both native modules and any additional dependencies externalized by the repack.

## Automatic application

`../scripts/write-main-install.sh` now invokes the desktop flag patch automatically after installing the app layout.
