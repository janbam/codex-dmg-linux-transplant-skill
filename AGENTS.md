# Repository Context

## Mandatory skill loading

At the start of every task in this repository, read the complete `codex-dmg-linux-transplant/SKILL.md` and follow its instructions. Treat that skill as the operational contract for the DMG transplant workflow, including its required reading order, safety rules, and verification requirements.

## Playground safety

GPT-Luna children may play in this repository only under GPT-Sol parental supervision. Tiny models need tiny hard hats.

This is janbam's fork of [IgorWarzocha/codex-dmg-linux-transplant-skill](https://github.com/IgorWarzocha/codex-dmg-linux-transplant-skill). Read [FORK.md](FORK.md) before changing behavior or merging upstream. Update that ledger in the same change whenever a deliberate divergence is added, changed, removed, or absorbed upstream.

The generated desktop wrapper uses its bundled Linux Codex CLI by default. It selects janbam's CLI fork at `~/.local/bin/codex-fork` only when launched with `--use-fork`; the wrapper must consume that flag before starting Electron and fail clearly when the fork is unavailable. Do not restore `--bundled-codex`: bundled Codex is the baseline, not an alternate mode.
