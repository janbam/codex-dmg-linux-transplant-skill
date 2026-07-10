# Desktop Flags Patch

`write-main-install.sh` patches recognized desktop-only flags after installing the app.

## Behavior

The renderer bundle changes between releases. The patch locates the component that emits `electron-desktop-features-changed`, replaces only that component, and keeps the surrounding module initialization intact.

It force-enables these flags when they exist in the current bundle:

- `avatarOverlay`
- `ambientSuggestions`
- `artifactsPane`
- `browserPane`
- `multiWindow`
- `projectlessThreads`

The July 2026 unified ChatGPT bundle currently exposes `ambientSuggestions`, `browserPane`, and `multiWindow` from that set. Platform-dependent computer-use flags are deliberately not forced: advertising unavailable macOS helpers on Linux creates broken UI.

## Manual use

```bash
../scripts/patch-desktop-flags.sh ~/.local/opt/codex-desktop
```

The script extracts and repacks `app.asar`, preserves externalized dependencies, and exits successfully without modifying the app when the known renderer pattern is absent. A recognized pattern that cannot be patched is an error.
