# Development Workflow

This document outlines a trunk-based workflow that keeps changes small and fast while ensuring releases always match the version in addon.xml and CHANGELOG.

## Goals
- Maintain quick PRs and frequent integration to `main`.
- Make the release version consistent across addon.xml, CHANGELOG, tags, and GitHub Releases.
- Keep CI as the gatekeeper: tests, lint, version checks.

## Development Environment Setup

### Prerequisites
- [uv](https://github.com/astral-sh/uv) - Modern Python package manager
- Python 3.9+
- Git

### Setup
1. Clone the repository and set up the environment:
   ```bash
   git clone https://github.com/yourusername/kodi.plugin.video.angelstudios.git
   cd kodi.plugin.video.angelstudios
   uv sync --dev
   source .venv/bin/activate
   ```

2. Run tests to verify setup:
   ```bash
   uv run make unittest-with-coverage
   ```

## Branching
- Short-lived branches off `main`:
  - `feat/...`, `fix/...`, `chore/...` → PR to `main`.
- Release branches:
  - `release/vX.Y.Z` only to finalize version/changelog; short-lived.
- Hotfixes:
  - `hotfix/vX.Y.Z+1` off `main` → PR to `main`.

## Main Protections
- Protect `main` via GitHub settings (self-PRs allowed for solo devs):
  - Require PRs to merge into `main`.
  - Require passing CI.
  - Optionally require 1 approval.
  - Prefer “Require linear history” to avoid merge commits (or use squash-merge).

## Version Source of Truth
- Version is set in the release PR and must be consistent across:
  - Addon version in [plugin.video.angelstudios/addon.xml](plugin.video.angelstudios/addon.xml)
  - Changelog entry in [CHANGELOG.md](CHANGELOG.md)
  - Tag `vX.Y.Z` on `main`
  - GitHub Release created by CI (notes from CHANGELOG)
- Optional helper: use `bump_version.py` to update addon.xml and CHANGELOG together.

## Release Flow
1. Develop and commit changes on `main`.
2. When ready for release, run the automated release process:
   ```bash
   kodi-addon-builder release minor --news "Description of changes"
   ```
3. This command will:
   - Bump version in addon.xml and pyproject.toml
   - Update CHANGELOG.md
   - Commit changes
   - Create and push git tag
   - Trigger GitHub Actions release workflow
4. CI validates the tagged commit, then creates GitHub release with addon zip.

## CI Gates
- On PRs to `main`:
  - Run tests with `uv run make unittest-with-coverage`
  - Enforce minimum 90% test coverage
  - Build addon zip artifact
- On tag `vX.Y.Z`:
  - Run full CI validation on tagged commit
  - Build versioned zip: `plugin.video.angelstudios-vX.Y.Z.zip`
  - Create GitHub release with auto-generated notes
  - Dispatch to central addon repository

## Changelog Discipline
- `kodi-addon-builder` automatically manages CHANGELOG.md entries.
- The tool creates dated sections like `## [0.5.0] - YYYY-MM-DD` for each release.
- Keep development commits descriptive as they become changelog entries.

## Hotfix Flow
- Apply fix directly on `main` or use `hotfix/...` branch.
- Use `kodi-addon-builder release patch --news "Hotfix description"` for automated patch release.
- CI will validate the fix and create the release.

## Example Commands
Release preparation:
```bash
# Ensure you're on main with clean working directory
git checkout main
git pull
uv run make unittest-with-coverage  # Verify tests pass

# Execute automated release
kodi-addon-builder release minor --news "Migrated to uv for modern Python dependency management, removed deprecated python-jose, extracted auth0-ciam-client, extensive code refactoring and cleanup, performance optimizations, and comprehensive testing improvements."
```

For review-before-commit:
```bash
# Just update files without committing
kodi-addon-builder bump minor --news "Description of changes"
# Review changes, then commit manually
git add .
git commit -m "chore(release): vX.Y.Z - Description"
kodi-addon-builder tag  # Creates and pushes the tag
```

## Policy Tweaks (Optional)
- `kodi-addon-builder` handles version consistency automatically.
- Enforce squash-merge on PRs for cleaner history.
- CI validates all releases through reusable workflows.

## Type Annotation Compatibility
- Target Python 3.9+ for type annotations to match KODI runtime environment.
- Use `typing.Optional` and `typing.Union` instead of `|` union syntax for Python 3.9 compatibility.
- Configure Pyright to target Python 3.9 via `[tool.pyright]` in `pyproject.toml`.
