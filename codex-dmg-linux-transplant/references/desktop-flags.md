# Desktop Flags Patch

`write-main-install.sh` patches recognized desktop-only flags after installing the app.

## Behavior

The renderer bundle changes between releases. The patch locates exactly one component that emits `electron-desktop-features-changed`, identifies its top-level feature properties from that semantic structure, and forces only recognized portable values. The publisher function, effect dependencies, unknown capabilities, and platform-dependent values remain upstream-authored. It never carries minified names, rebuilds the dispatch object, or globally replaces gate calls between releases.

It force-enables these flags when they exist in the current bundle:

- `avatarOverlay`
- `ambientSuggestions`
- `artifactsPane`
- `browserPane`
- `multiWindow`
- `projectlessThreads`

ChatGPT 26.715.70719 build 5650 exposes `ambientSuggestions`, `browserPane`, and `multiWindow` from that set. Platform-dependent computer-use flags are deliberately not forced: advertising unavailable macOS helpers on Linux creates broken UI.

The semantic boundary is deliberate. Minifiers routinely reuse short identifiers for unrelated functions; replacing a release-local call such as `Yp()` across the renderer can silently corrupt navigation or other application logic. Rebuilding the dispatch object is also unsafe because new upstream capability fields would disappear. If the stable dispatch is missing, duplicated, or structurally ambiguous, the patcher skips or fails clearly instead of guessing.

On Linux, the same patch phase also clarifies the unsupported dictation message. The unavailable feature is the system-wide dictation shortcut and injection service; in-app composer dictation remains available. The copy rewrite is bound to the stable `settings.voice.dictation.unsupported` translation descriptor and patches both the runtime view and generated settings-search document when present.

## Manual use

```bash
../scripts/patch-desktop-flags.sh ~/.local/opt/codex-desktop
```

The script extracts `resources/app.asar`, materializes placeholders for missing unpacked dev-only files in one pass, formats the semantic candidate for deterministic structural discovery, patches the renderer bundle, and repacks `app.asar` while preserving both native modules and any additional dependencies externalized by the repack.

When the known renderer pattern is absent, the script exits successfully without modifying the app. A recognized pattern that cannot be patched is an error.

## Automatic application

`../scripts/write-main-install.sh` now invokes the desktop flag patch automatically after installing the app layout.
