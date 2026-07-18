# ChatGPT Desktop DMG Linux Transplant Skill

OpenAI renamed the Codex desktop app to ChatGPT and folded Chat, ChatGPT Work, and Codex into one app. This skill transplants that macOS app to Linux when no official Linux build is available.

It handles fresh installs, updates, and repairs from the current unified ChatGPT DMG. The visible desktop entry is **ChatGPT**, while the stable local paths and `codex://` protocol remain unchanged for compatibility with upstream internals.

The skill:

- finds a local DMG or downloads the current `ChatGPT.dmg`
- discovers the unified `ChatGPT.app` bundle layout
- reads the app, Electron, build, native dependency, and bundled Codex CLI versions from the DMG
- extracts the default ChatGPT icon plus external plugin and skill resources
- removes unusable macOS binaries from copied plugin resources
- installs the exact matching Linux Codex CLI while narrowly bypassing local npm age gates
- rebuilds `better-sqlite3` and `node-pty` for Linux
- patches recognized desktop UI flags
- replaces the main install instead of creating versioned copies
- verifies the final wrapper rather than stopping at a staged build
- reports Desktop update availability with `codex-desktop --check-update`

Default sources:

- DMG: `https://persistent.oaistatic.com/codex-app-prod/ChatGPT.dmg`
- release feed: `https://persistent.oaistatic.com/codex-app-prod/appcast.xml`

Tested against ChatGPT Desktop **26.707.31428** (build **5059**, Electron **42.1.0**), published July 9, 2026. Legacy `Codex.dmg` bundles are intentionally unsupported.
