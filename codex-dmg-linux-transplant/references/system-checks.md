# System Checks

Inspect the machine before planning the transplant.

## Probe

Run:

```bash
../scripts/probe-system.sh
```

Confirm:

- distro and architecture
- package manager
- `python3`, `node`, `npm`, `git`, `curl`, and `7z`
- `gcc`, `g++`, and `make`
- `xdg-mime` and `update-desktop-database`
- Python packaging support for Pillow
- existing Electron binaries
- existing Codex or ChatGPT launchers, desktop files, and install directories

Then run:

```bash
../scripts/ensure-prereqs.sh
```

This command only validates prerequisites. When it reports missing commands, stop and ask the human operator to install them; do not run `sudo` or change system packages from Codex.

Do not continue without Python, Node/npm, 7-Zip, a working C/C++ toolchain, and the XDG desktop integration tools.

## Existing install search

Inspect:

- `~/.local/bin/*codex*` and `~/.local/bin/*chatgpt*`
- `~/.local/share/applications/*codex*.desktop`
- `~/.local/share/applications/*chatgpt*.desktop`
- `~/.local/opt/codex-desktop*`
- `/opt/*codex*`, `/opt/*chatgpt*`, and matching `/usr/bin` entries

The final result should still be one main install, not parallel Codex and ChatGPT copies.

## DMG requirements

The extractor must find one top-level Electron `.app` containing:

- `Info.plist`
- `Resources/app.asar`
- `Resources/app.asar.unpacked`
- the icon named by `CFBundleIconFile`

Current ChatGPT builds also supply `Resources/plugins` and `Resources/skills`; preserve their portable contents.
