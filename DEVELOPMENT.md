# Development Workflow

This document outlines a trunk-based workflow that keeps changes small and fast while ensuring releases always match the version in addon.xml and CHANGELOG.

## Goals
- Maintain quick PRs and frequent integration to `main`.
- Make the release version consistent across addon.xml, CHANGELOG, tags, and GitHub Releases.
- Keep CI as the gatekeeper: tests, lint, version checks.

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
1. Prepare a release branch:
   - Branch: `release/vX.Y.Z` from `main`.
   - Update addon version in [plugin.video.angelstudios/addon.xml](plugin.video.angelstudios/addon.xml).
   - Move "Unreleased" changes into a new `X.Y.Z - YYYY-MM-DD` section at the top of [CHANGELOG.md](CHANGELOG.md).
   - Commit: `chore(release): vX.Y.Z`.
   - Push and open a PR to `main`.
2. Merge:
   - CI passes → merge release PR to `main`.
3. Tag and publish:
   - Create annotated tag `vX.Y.Z` on the merge commit.
   - Push tag to trigger the release workflow in [.github/workflows/release.yml](.github/workflows/release.yml).
   - CI validates versions, builds the addon zip, and publishes a GitHub Release with artifacts.

## CI Gates
- On PRs to `main`:
  - Run tests and coverage.
  - Lint/format (optional).
  - If branch is `release/vX.Y.Z`:
    - Verify addon.xml version equals `X.Y.Z`.
    - Verify CHANGELOG contains a top-level `X.Y.Z` section (no leftover "Unreleased" for included changes).
- On tag `vX.Y.Z`:
  - Compare tag version with addon.xml. Fail if mismatch.
  - Build/publish via [.github/workflows/release.yml](.github/workflows/release.yml).

## Changelog Discipline
- Keep an "Unreleased" section at the top and accumulate entries via normal PRs.
- In the release PR:
  - Move "Unreleased" into a dated `X.Y.Z - YYYY-MM-DD` section.
  - Create a fresh empty "Unreleased" section for the next cycle.

## Hotfix Flow
- Branch `hotfix/vX.Y.Z+1` from `main`.
- Apply minimal fix and bump patch version in addon.xml and CHANGELOG.
- PR → merge → tag `vX.Y.Z+1` → CI publishes.

## Example Commands
Prepare release:
```bash
# Create release branch
git checkout -b release/v1.2.3

# Update addon.xml + CHANGELOG (or run bump_version.py)
# ... edit files ...

# Commit and push
git add plugin.video.angelstudios/addon.xml CHANGELOG.md
git commit -m "chore(release): v1.2.3"
git push -u origin release/v1.2.3

# Open PR to main in GitHub
```
After merge:
```bash
# Ensure you’re on the merge commit
git checkout main
git pull

# Tag and push
git tag -a v1.2.3 -m "v1.2.3"
git push origin v1.2.3
```

## Policy Tweaks (Optional)
- Require that release PRs only touch addon.xml, CHANGELOG, and any version tooling.
- Enforce squash-merge on PRs for cleaner history.
- Add lightweight CI checks to validate addon.xml ↔ tag ↔ CHANGELOG consistency.
