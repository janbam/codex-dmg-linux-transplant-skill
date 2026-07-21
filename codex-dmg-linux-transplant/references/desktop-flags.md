# Desktop Flags Patch

`write-main-install.sh` patches recognized desktop-only flags after installing the app.

## Behavior

The renderer bundle changes between releases. The patch locates exactly one component that emits `electron-desktop-features-changed`, discovers its current minified function, Electron bridge, and React aliases from that semantic structure, and replaces only that component. It never carries minified names or globally replaces gate calls between releases.

It force-enables these flags when they exist in the current bundle:

- `avatarOverlay`
- `ambientSuggestions`
- `artifactsPane`
- `browserPane`
- `multiWindow`
- `projectlessThreads`

ChatGPT 26.715.70719 build 5650 exposes `ambientSuggestions`, `browserPane`, and `multiWindow` from that set. Platform-dependent computer-use flags are deliberately not forced: advertising unavailable macOS helpers on Linux creates broken UI.

The semantic boundary is deliberate. Minifiers routinely reuse short identifiers for unrelated functions; replacing a release-local call such as `Yp()` across the renderer can silently corrupt navigation or other application logic. If the stable dispatch is missing, duplicated, or structurally ambiguous, the patcher skips or fails clearly instead of guessing.

## Manual use

```bash
../scripts/patch-desktop-flags.sh ~/.local/opt/codex-desktop
```

The script extracts `resources/app.asar`, materializes placeholders for missing unpacked dev-only files in one pass, formats the semantic candidate for deterministic structural discovery, patches the renderer bundle, and repacks `app.asar` while preserving both native modules and any additional dependencies externalized by the repack.

When the known renderer pattern is absent, the script exits successfully without modifying the app. A recognized pattern that cannot be patched is an error.

## Automatic application

`../scripts/write-main-install.sh` now invokes the desktop flag patch automatically after installing the app layout.
