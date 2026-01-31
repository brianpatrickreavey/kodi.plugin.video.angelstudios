# BUILD.md

## Kodi Addon Development, Build & Release Process

This document describes the development, build and release workflow for this
Kodi addon, including versioning, branch conventions, and GitHub Actions automation.

---

## Development Environment Setup

### Prerequisites
- [uv](https://github.com/astral-sh/uv) - Modern Python package manager
- Python 3.9+
- Git

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/kodi.plugin.video.angelstudios.git
   cd kodi.plugin.video.angelstudios
   ```

2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Set up the development environment:
   ```bash
   uv sync --dev
   ```

4. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```

5. Run tests to verify setup:
   ```bash
   uv run make unittest-with-coverage
   ```

### Development Workflow
Development is best done with a local instance of KODI configured to use your
live code as an addon. In Linux, this can be accomplished by creating a
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

The first time you launch KODI after creating the symlink, KODI will prompt you
if you want to enable the addon, and you should answer yes. At this point,
the plugin is live within KODI.

While some changes to code may take effect "live", it is best to quit KODI and
re-launch it to ensure you are running the latest code.

## Branching & Versioning Strategy
We are following trunk-based development. All commits are made to `main`
unless there is a need for a short-lived release branch.

When the code is ready for a release, use the `kodi-addon-builder` tool to
automate versioning, changelog management, and Git operations. This project
follows `semver` versioning. Every release must include "news" describing the
updates. The process is largely automated:

### Release Preparation
1. Ensure all changes for the release are committed and tested locally
2. Run `uv run make unittest-with-coverage` to verify tests pass with ≥90% coverage
3. Ensure the working directory is clean (no uncommitted changes)

### Automated Release Process
Use `kodi-addon-builder` commands for releases:

#### For Minor/Patch Releases:
```bash
# Bump version, update changelog, commit, tag, and push in one command
kodi-addon-builder release minor --news "Brief description of changes"
# or
kodi-addon-builder release patch --news "Brief description of changes"
```

#### For Review-Before-Commit (if you prefer to inspect changes):
```bash
# Just update files without committing
kodi-addon-builder bump minor --news "Brief description of changes"
# Review the changes, then commit manually
git add .
git commit -m "chore(release): vX.Y.Z - Brief description"
# Then create tag and push
kodi-addon-builder tag  # Creates and pushes the tag
```

The `kodi-addon-builder release` command will:
- Bump versions in `addon.xml` and `pyproject.toml` to the new version
- Automatically add the news entry to `<news>` in `addon.xml`
- Append a new entry to `CHANGELOG.md` (e.g., `## [0.5.0] - YYYY-MM-DD`)
- Commit all changes with the news as the commit message
- Create a git tag for the new version
- Push the commit and tag to remote
- Trigger the GitHub Actions release workflow

### Manual Process (Fallback)
If `kodi-addon-builder` encounters issues, the manual process is:

1. Bump the version: run `bump_version.py`. The script will prompt for a
   type of bump (major|minor|patch) and for the "news" related to the
   release. These will be substituted into the `addon.xml` file with the
   new version number. The new version number will also be output to the
   terminal (you will need this later).
2. Commit the new `addon.xml`.
   ```bash
   git add plugin.video.angelstudios/addon.xml
   git commit -m "Your News Here"
   ```
3. Push the new `addon.xml` to GitHub
   ```bash
   git push
   ```
4. Tag the build with the version from `bump_version.py`
   ```bash
   git tag v0.1.5
   ```
5. Push the tag to origin with the same version number
   ```bash
   git push origin v0.1.5
   ```

---

## Automated Build & Release (GitHub Actions)

### Workflow Triggers

- **CI Workflow** (`.github/workflows/ci.yml`):
  - On push to `main` or pull requests to `main`
  - Runs tests with `uv`, enforces ≥90% coverage, builds addon zip
  - Fails build if coverage <90% or tests fail

- **Release Workflow** (`.github/workflows/release.yml`):
  - On push of version tags (`v*`)
  - Calls CI workflow first to ensure code quality
  - Only proceeds with release if CI passes
  - Creates GitHub release with addon zip

### CI Steps

1. **Environment Setup**
   - Installs `uv` and sets up Python 3.9
   - Syncs dependencies with `uv sync --dev`

2. **Testing & Quality**
   - Runs `uv run make unittest-with-coverage`
   - Enforces minimum 90% test coverage
   - Fails if tests fail or coverage <90%

3. **Build**
   - Creates addon zip artifact using `kodi-addon-builder zip`

### Release Steps

1. **CI Validation**
   - Runs the full CI workflow on the tagged commit
   - Ensures all tests pass and coverage ≥90%

2. **Release Creation**
   - Builds versioned zip: `plugin.video.angelstudios-vX.Y.Z.zip`
   - Creates GitHub release with auto-generated notes
   - Dispatches to central addon repository

3. **Artifact Upload**
   - Uploads zip as release asset
   - Triggers downstream addon repository updates

---

## Pre-commit Hook

A pre-commit hook is provided to enforce correct versioning and branch
discipline:

```bash
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
ADDON_XML="plugin.video.angelstudios/addon.xml"

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
process using `kodi-addon-builder`:

### 1. Develop Features

- Work on new features or bugfixes directly on `main` (trunk-based development).
- Ensure all changes are tested and meet ≥90% coverage requirement.
- Commit changes with descriptive messages.

### 2. Prepare Release

- When ready to release, ensure you're on `main` with all changes committed:
  ```bash
  git checkout main
  git pull
  uv run make unittest-with-coverage  # Verify tests pass locally
  git status  # Ensure working directory is clean
  ```

### 3. Execute Automated Release

- Use `kodi-addon-builder` for a fully automated release:
  ```bash
  kodi-addon-builder release minor --news "Migrated to uv for modern Python dependency management, removed deprecated python-jose, extracted auth0-ciam-client, extensive code refactoring and cleanup, performance optimizations, and comprehensive testing improvements."
  ```

This single command will:
- Bump version to 0.5.0
- Update `addon.xml` and `CHANGELOG.md`
- Commit changes with descriptive message
- Create and push git tag `v0.5.0`
- Trigger GitHub Actions release workflow

### 4. Monitor Release

- GitHub Actions will:
  - Run CI on the tagged commit (verify tests and ≥90% coverage)
  - If CI passes, create GitHub release with addon zip
  - Dispatch to central addon repository for distribution

### Summary Table

| Step | Action                                      | Tool/Command |
|------|---------------------------------------------|--------------|
| 1    | Develop features on main, ensure tests pass | `uv run make unittest-with-coverage` |
| 2    | Prepare for release (verify clean state)    | `git status` |
| 3    | Execute automated release                   | `kodi-addon-builder release minor --news "..."` |
| 4    | Monitor CI and release creation             | GitHub Actions |

---

This process leverages `kodi-addon-builder` for automation while maintaining
version discipline and reproducible releases through GitHub Actions CI/CD.
