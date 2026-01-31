# Kodi Addon Angel Studios - 0.5.0 Release Preparation Plan

This plan outlines the steps to prepare for the 0.5.0 release of the Kodi addon, incorporating `kodi-addon-builder` for automated versioning, changelog management, and release operations. This builds on the uv migration, auth0-ciam-client extraction, and other updates since v0.4.1.

## Prerequisites
- All code changes for 0.5.0 are complete and tested locally
- Run `make unittest-with-coverage` to ensure minimum 90% unit test coverage (target: 100% by v1.0.0)
- Ensure the working directory is clean (no uncommitted changes)
- `kodi-addon-builder` is installed as a dev dependency

## Release Steps Using kodi-addon-builder

### 1. Update CI/CD Pipelines ✅ COMPLETED
- Replace any references to pip, pipenv, or pyenv with uv commands (e.g., `uv sync` for dependencies, `uv run` for test execution).
- **Implemented**: Created `.github/workflows/ci.yml` for automated testing on push/PR to main/master branches
  - Uses `uv` for dependency management and test execution
  - Runs `make unittest-with-coverage` to ensure 100% test coverage
  - Builds addon zip and uploads as artifact
- **Implemented**: Updated `.github/workflows/release.yml` to use reusable workflows
  - Release workflow now calls CI workflow first before proceeding with release
  - Ensures tagged code passes all tests before creating releases
  - Triggers only on version tags (v*)
- Ensure the workflow integrates with `kodi-addon-builder` for any release automation (e.g., triggering on tags created by the tool).

### 2. Update Documentation ✅ COMPLETED
- Revise README.md, DEVELOPMENT.md, and BUILD.md to mention uv instead of pipenv/pyenv.
- Update installation instructions to include uv installation and usage.
- Archive or update any docs referencing removed tools (e.g., requirements.txt).
- Add a section on using `kodi-addon-builder` for releases (e.g., "Use `kodi-addon-builder bump-commit minor --news '...' ` for version bumps").
- **Completed**: Updated all documentation files with uv setup instructions and kodi-addon-builder workflow.

### 3. Validate Dependencies and Compatibility
- Confirm all dependencies in pyproject.toml are correct and uv.lock is up-to-date.
- Test the addon on target Kodi versions to ensure no regressions from the refactoring.
- Run `kodi-addon-builder bump patch --dry-run` to validate addon.xml parsing and version detection.

### 4. Run Comprehensive Testing
- Execute `make unittest-with-coverage` locally to achieve 100% coverage.
- Run integration tests or manual checks for key features (e.g., authentication, content loading).
- Use `kodi-addon-builder zip --dry-run` to test zip generation without creating files.

### 5. Update CHANGELOG.md and Version Files (Automated with kodi-addon-builder)
- Use `kodi-addon-builder bump-commit minor --news "Migrated to uv for modern Python dependency management, removed deprecated python-jose, extracted auth0-ciam-client, extensive code refactoring and cleanup, performance optimizations, and comprehensive testing improvements."` to:
  - Bump versions in addon.xml and pyproject.toml to 0.5.0.
  - Automatically add the news entry to `<news>` in addon.xml.
  - Append a new entry to CHANGELOG.md (e.g., `## [0.5.0] - YYYY-MM-DD\n- Migrated to uv...`).
  - Commit all changes with the news as the commit message.
- **Alternative**: If you prefer to review before committing, use `kodi-addon-builder bump minor --news "..."` then manually commit.

### 6. Code Cleanup and Final Checks
- Remove any lingering references to old tools (e.g., in comments or scripts).
- Ensure .gitignore includes uv.lock and excludes old files like requirements.txt.
- Verify no broken imports or deprecated code.
- Run `kodi-addon-builder bump patch --dry-run` to confirm no XML parsing errors.

### 7. Release Preparation (Automated with kodi-addon-builder)
- After committing the version bump, use `kodi-addon-builder release minor --news "Migrated to uv for modern Python dependency management, removed deprecated python-jose, extracted auth0-ciam-client, extensive code refactoring and cleanup, performance optimizations, and comprehensive testing improvements."` to:
  - Bump version (if not already done).
  - Commit changes (if not already done).
  - Create a git tag for v0.5.0.
  - Push the commit and tag to remote.
- Test the release workflow (e.g., release.yml) to ensure it runs CI first, packages correctly, and creates the GitHub release with the zip.
- Prepare release notes or announcements highlighting the tooling upgrade.

### 8. Post-Release Planning (Optional but Recommended)
- Monitor CI for any failures after release.
- Update any external dependencies or repos that reference this addon.
- If issues arise, use `kodi-addon-builder` commands for hotfixes (e.g., `bump-commit patch --news "Fix..."`).

## Verification Steps
- Check that `addon.xml` shows version `0.5.0`
- Verify `CHANGELOG.md` has the new entry
- Confirm GitHub release is created with the zip download
- Test the zip in Kodi to ensure it works

## Fallback Manual Steps (if needed)
- If `kodi-addon-builder` encounters issues: Manually update `addon.xml` version and changelog, then use `commit`, `tag`, and `push` commands individually

This plan reduces manual steps from ~8-10 to just 1-2 `kodi-addon-builder` commands, with built-in safety checks (tree cleanliness, changelog enforcement) and automated Git operations. The tool ensures consistent versioning and release practices across your Kodi addon projects.