# BUILD.md

## Kodi Addon Development, Build & Release Process

This document describes the development, build and release workflow for this
Kodi addon, including versioning, branch conventions, and GitHub Actions automation.

---

## Development

Development is best done with a local instance of KODI configured to use your
live code as an addon.  In Linux, this can be accomplished by creating a
symbolic link between your code directory and a directory in the KODI addons
directory.

```bash
ln -sf {your_code_directory} {addon_directory}
```

For example, on my system it looks like:

```bash
ln -sfT ~/Code/kodi.plugin.video.angelstudios/plugin.video.angelstudios \
    ~/.kodi/addons/plugin.video.angelstudios
ls -l ~/.kodi/addons/plugin.video.angelstudios
```

You should see output similar to:

```bash
lrwxrwxrwx 1 bpreavey bpreavey 50 Jul 28 14:53
/home/bpreavey/.kodi/addons/kodi.plugin.video.angelstudios/plugin.video.angelstudios -> /home/bpreavey/Code/plugin.video.angelstudios
```

The first time you launch KODI after creating the symlnk, KODI will prompt you
if you want to enable the addon, and you should answer yes.  At this point,
the plugin is live within KODI.

While some changes to code may take effect "live", it is best to quit KODI and
re-launch it to ensure you are running the latest code.

## Branching & Versioning Strategy
We are following trunk-based development.  All commits are made to `main`
unless there is a need for a short-lived release branch.

When the code is ready for a release, update addon.xml to the next correct
version.  This project follows `semver` versioning.  Every releage must
include "news" describing the updates.  Most of this process is automated,
but there are a few steps to follow:

1. Bump the version: run `bump_version.py`.  The script will prompt for a
   type of bump (major|minor|patch) and for the "news" related to the
   release.  These will be substituted into the `addon.xml` file with the
   new version number.  The new version number will also be output to the
   terminal (you will need this later).
2. Commit the new `addon.xml`.
   ``` bash
   git add plugin.video.angelstudios/addon.xml

   ```


```xml
<?xml version="1.0" encoding="UTF-8"?>
<addon id="plugin.video.angelstudios" version="1.0.1" name="Angel Studios">
...
```

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
   - For release branches, appends `-rcN`
     (e.g., `plugin.video.angelstudios-1.2.0-rc2.zip`).

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

A pre-commit hook is provided to enforce correct versioning and branch
discipline:

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
    echo "❌ Direct commits to main are not allowed."
    echo "Please use a release branch and open a pull request."
    exit 1
fi
```

Place this in `.git/hooks/pre-commit` and make it executable (`chmod +x .git/hooks/pre-commit`).

- On `release/x.y.z` branches, the hook enforces that the version in
  `addon.xml` matches the branch version.
- On `main`, the hook blocks direct commits (all changes should come from a
  release branch via pull request).
- On `develop` and feature branches, no checks are enforced.

---

## Manual Version Bumping

- Always update the `version` attribute in `addon.xml` before creating a
  release branch or merging to `main`.
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

## Recommended Release Workflow

Follow these steps to ensure a clean, reproducible, and automated release
process:

### 1. Develop Features

- Work on new features or bugfixes in feature branches (`feature/xyz`) or
  directly on `develop`.
- Merge feature branches into `develop` as features are completed.

### 2. Create a Release Branch

- When ready to prepare a release, create a release branch from `develop`:

  ```bash
  git checkout develop
  git pull
  git checkout -b release/x.y.z
  ```

- Update the `version` attribute in `addon.xml` to match the release version
  (`x.y.z`).

### 3. Finalize the Release Branch

- Perform final testing, bugfixes, and polish on the `release/x.y.z` branch.
- Each push to the release branch triggers a build and creates a pre-release
  (`-rcN`).

### 4. Merge Release Branch into Main

- When the release is ready, merge the release branch into `main` (squash
  commits for a clean history):

  ```bash
  git checkout main
  git pull
  git merge --squash release/x.y.z
  git commit -m "Release x.y.z"
  git push
  ```

- The workflow will build and create the final release artifact from `main`.

### 5. Rebase Develop Off Main

- Bring `develop` up to date with `main` to ensure it contains all hotfixes and
  release changes:

  ```bash
  git checkout develop
  git pull
  git rebase main
  ```

### Summary Table

| Step | Branch         | Action                                      |
|------|---------------|---------------------------------------------|
| 1    | feature/*, develop | Develop features, merge to develop         |
| 2    | release/x.y.z | Create from develop, bump version           |
| 3    | release/x.y.z | Finalize, test, fix bugs, pre-releases      |
| 4    | main          | Merge release branch (squash), final release|
| 5    | develop       | Rebase develop off main                     |

---

This process keeps `main` clean and production-ready, allows for parallel
feature development, and ensures version discipline and reproducible releases.
