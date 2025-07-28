# BUILD.md

## Kodi Addon Build & Release Process

This document describes the build and release workflow for this Kodi addon, including versioning, branch conventions, and GitHub Actions automation.

---

## Branching & Versioning Strategy

- **Development** occurs on the `develop` branch.
- **Production releases** are merged to the `main` branch.
- **Release candidates** are created from branches named `release/x.y.z` (e.g., `release/1.2.0`).
- The version in `addon.xml` **must match** the version in the release branch name (e.g., `release/1.2.0` → `1.2.0` in `addon.xml`).

---

## Automated Build & Release (GitHub Actions)

### Workflow Triggers

- On push to `main`, `develop`, or any `release/x.y.z` branch.
- Manually via the GitHub Actions UI.

### Steps

1. **Version Check (Release Branches Only)**
   - Ensures the version in `addon.xml` matches the version in the branch name.
   - Fails the build if they do not match.

2. **RC Number Detection (Release Branches Only)**
   - Checks for previous `-rcN` (release candidate) tags for the current version.
   - Increments the RC number for each new build from the same release branch.

3. **Zip Build**
   - Builds a zip file named `<addon-id>-<version>.zip` for `main` and `develop`.
   - For release branches, appends `-rcN` (e.g., `plugin.video.angelstudios-1.2.0-rc2.zip`).

4. **Artifact Upload**
   - Uploads the zip file as a workflow artifact.

5. **GitHub Release**
   - Creates a GitHub Release with the appropriate tag:
     - `v<version>` for `main`
     - `v<version>-rcN` for release branches
   - Marks release branches as pre-releases.
   - Attaches the zip file to the release.

---

## Pre-commit Hook

A pre-commit hook is provided to enforce correct versioning and branch discipline:

```bash
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
ADDON_XML="addon.xml"

# Enforce version match on release branches
if [[ "$BRANCH" =~ ^release/ ]]; then
    BRANCH_VERSION="${BRANCH#release/}"
    CUR_VERSION=$(grep -oP 'version="\K[^"]+' $ADDON_XML)
    if [ "$BRANCH_VERSION" != "$CUR_VERSION" ]; then
        echo "❌ Version mismatch: branch is '$BRANCH', but addon.xml is '$CUR_VERSION'"
        echo "Please update addon.xml to match the branch version."
        exit 1
    fi
fi

# Block direct commits to main
if [[ "$BRANCH" == "main" ]]; then
    echo "❌ Direct commits to main are not allowed. Please use a release branch and open a pull request."
    exit 1
fi
```

Place this in `.git/hooks/pre-commit` and make it executable (`chmod +x .git/hooks/pre-commit`).

- On `release/x.y.z` branches, the hook enforces that the version in `addon.xml` matches the branch version.
- On `main`, the hook blocks direct commits (all changes should come from a release branch via pull request).
- On `develop` and feature branches, no checks are enforced.

---

## Manual Version Bumping

- Always update the `version` attribute in `addon.xml` before creating a release branch or merging to `main`.
- The workflow will enforce this for release branches.

---

## Example Release Flow

1. Finish development on `develop`.
2. Create a release branch:  
   `git checkout -b release/1.2.0`
3. Update `addon.xml` to `1.2.0`.
4. Push the branch to GitHub.
5. The workflow will build and create a pre-release with `-rc1`.
6. Subsequent pushes to the same branch will increment the RC number.
7. When ready, merge to `main` for the final release.

---

## Notes

- Only stable releases should be merged to `main`.
- Pre-releases (`-rcN`) are for testing and review.
- The workflow automates artifact creation and release management, reducing manual steps