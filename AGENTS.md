# Agent Instructions

Kodi addon `plugin.video.angelstudios`. Read [`.github/copilot-instructions.md`](.github/copilot-instructions.md) and [`agents/README.md`](agents/README.md).

Exploration is the default. Answer questions and design options in text. Change files when the user asks for a change or a result. A "?" does not cancel a request, and a missing "?" does not turn a speculative idea into a task. If a message mixes both, do the task and answer the question. Do not implement the answer in the same turn. See `~/.grok/rules/explore-before-implement.md`.

Ship steps are in `~/Code/kodi-development/README.md`.

On a new machine:

```bash
git clone https://github.com/brianpatrickreavey/kodi.plugin.video.angelstudios.git
cd kodi.plugin.video.angelstudios
uv sync
```

Branches: `main` (releases), `develop` (refactor WIP), `feature/auth-refactor`.

Related research: private repo `angel-scraper`. Auth library: `auth0-ciam-client` / `kodi.script.module.auth0-ciam-client`.
