# System Checks

Always inspect the machine before planning the transplant.

## Required probes

Run:

```bash
../scripts/probe-system.sh
```

That probe should confirm:

- OS and distro from `/etc/os-release`
- architecture from `uname -m`
- available package manager(s)
- required tools:
  - `python3`
  - `node`
  - `npm`
  - `git`
  - `curl`
  - `7z`
- build tools:
  - `gcc`
  - `g++`
  - `make`
- Python packaging support for installing Pillow if needed
- existing Electron binaries, if any
- existing Codex launchers, desktop files, and install directories

## Prerequisite install step

After probing, run:

```bash
../scripts/ensure-prereqs.sh
```

This should install missing dependencies for supported distros before the transplant proceeds.

## Fail-fast rules

Do not continue until these exist:

- `python3`
- `node`
- `npm`
- `7z`
- a working C/C++ toolchain for native rebuilds

## Existing install inspection

The user asked for a single main desktop version. Check and later clean up:

- `~/.local/bin/codex-desktop*`
- `~/.local/share/applications/*codex*.desktop`
- `~/.local/opt/codex-desktop*`
- `/opt/codex-desktop*`
- `/usr/bin/codex-desktop`

## DMG asset requirement

The transplant must extract both:

- `app.asar`
- `app.asar.unpacked`
- the default Codex icon from the DMG

Do not ship a placeholder icon.
