# Fork Divergences

This ledger records intentional differences from [`IgorWarzocha/codex-dmg-linux-transplant-skill`](https://github.com/IgorWarzocha/codex-dmg-linux-transplant-skill). Keep it focused on behavior, policy, and durable fork-owned artifacts rather than incidental textual differences.

## Active divergences

### Codex CLI selection

- The generated desktop wrapper uses the bundled Linux Codex CLI deterministically, ignoring ambient `CODEX_CLI_PATH` and globally installed `codex` commands.
- `--use-fork` selects the executable regular file at `~/.local/bin/codex-fork` for one launch and is consumed before Electron starts.
- The fork-added `--bundled-codex` selector is rejected because bundled Codex is now the default.

### Electron installation safety

- When npm lifecycle scripts are disabled, Electron's package-local `install.js` runs only after the operator explicitly sets `CODEX_TRANSPLANT_RUN_ELECTRON_INSTALL_JS=1`.
- The skill does not silently run that installer or fall back to downloading a runtime executable directly.

### Chromium sandbox policy

- The workflow forbids `--no-sandbox` and requires `chrome-sandbox` to use `root:root` ownership with mode `4755`.
- Root-only ownership and mode changes are handed to the human operator explicitly.

### Failed-install preservation

- If desktop flag patching fails, the new install is moved back to its original staging path and the previous install is restored.
- A failed fresh install therefore preserves the expensive stage instead of deleting it.

### End-to-end verification

- Completion requires successful login and at least one live smoke test from the installed desktop app, not merely a launchable wrapper.

### Transplant records

- `reports/` contains fork-owned reports for successfully transplanted Codex Desktop builds and the operational lessons folded back into the skill.

## Maintenance

Update this file in the same commit as any new or changed divergence. During upstream merges, remove or rewrite entries that upstream has absorbed so the ledger describes the current tree rather than its archaeology.
