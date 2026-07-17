# Repository Context

This is janbam's fork of [IgorWarzocha/codex-dmg-linux-transplant-skill](https://github.com/IgorWarzocha/codex-dmg-linux-transplant-skill). Read [FORK.md](FORK.md) before changing behavior or merging upstream. Update that ledger in the same change whenever a deliberate divergence is added, changed, removed, or absorbed upstream.

The generated desktop wrapper uses its bundled Linux Codex CLI by default. It selects janbam's CLI fork at `~/.local/bin/codex-fork` only when launched with `--use-fork`; the wrapper must consume that flag before starting Electron and fail clearly when the fork is unavailable. Do not restore `--bundled-codex`: bundled Codex is the baseline, not an alternate mode.
