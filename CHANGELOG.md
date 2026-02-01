# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.1] - 2026-01-07
- bugfix: erroneous attempt to set duration on unavailable episodes resulted in episode_menu errors.  updated duration logic to be gated by episode availability.
- [Bug-fix] Handle unavailable episodes (source: None) without crashing

## [0.4.0] - 2026-01-07
- Major refactor, menu building, debug and trace settings, etc.
- Feat: Enhanced Kodi UI, streaming, debugging, and API tracing
- i18n: reorganize strings.po into logical sections and update settings.xml references; replace hardcoded labels with IDs/core strings; add missing entries

## [0.3.1] - 2026-01-02
- Fix unplayable ListItems.  Slight refactor of item creation for consistency.
- Refactor: ListItem creation in KodiUIInterface to improve episode handling and playback properties.  FIX: Fix unplayable items

## [0.3.0] - 2026-01-02
- Unit Test coverage at 100%.  Small tweaks to code as unit tests uncovered minor issues.
- FEATURE: start testing framework.  break out unit test structure.  refactor quite a bit of kodi_ui_interface.py as testing uncovered old code and redundant processing.

## [0.2.2] - 2025-12-23
- remove unecessary file operation

## [0.2.1] - 2025-12-23
- fixing simplecache install issues

## [0.2.0] - 2025-12-23
- Fix episode handling for unavailable episodes
- Updated Episode parser to handle unavailable episodes Other cleanup items

## [0.1.4] - 2025-12-23
- testing tag-based workflow

## [0.1.3] - 2025-12-23
- testing tag-based build process

## [0.1.2] - 2025-12-23
- Release patch for 0.1.2
- Renaming ZIP file to no longer prepend "kodi" to the front.

## [0.1.1-test] - 2025-12-23
- update build process to have correct name and version in teh zipfile name

## [0.1.0-test] - 2025-12-23
- Update addon.xml to test tagging triggers
- REFACTOR: iterating on the new workflow.
- REFACTOR - step 1, moving files to new subdirectories and working on .gitattributes for a easy ZIP process
- Update .gitignore to exclude .pkl files and modify symlink command in BUILD.md
- Remove unused binary files: new_dev_shell_angel_session.pkl and temp.pickle
- Update BUILD.md to enhance development instructions and clarify release workflow
- Fix regex for release branch detection in zip file naming
- Refactor GitHub Actions workflow to ensure conditional steps for main and release branches
- Refactor GitHub Actions workflow to use softprops/action-gh-release for creating releases and uploading assets