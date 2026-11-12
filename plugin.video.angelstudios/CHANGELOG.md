# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [0.10.0] - 2026-11-11
- Show the signed-in watchlist and add or remove movies, series, and specials.

## [0.9.0] - 2026-11-11
- Play closed captions from the Angel stream.

## [0.8.0] - 2026-11-10
- Show the watch-page title tags on movies, series, and specials.

## [0.7.0] - 2026-11-10
- Revoke the Angel session on logout

## [0.6.1] - 2026-11-10
- Recognize the resolved stream as this episode.

## [0.6.0] - 2026-11-09
- Send watch progress to Angel during playback and resume catalog titles from that position.
- Clear Kodi's stored stop so resume stays on Angel's position.
- A title with no saved position starts at the beginning. A failed read keeps the cached time.

## [0.5.9] - 2026-11-08
- Stop requesting `primaryFlowPhases`. Angel's phase-manager service is refusing connections, and that error was hiding the seasons.

## [0.5.8] - 2026-11-02
- Add the setting Log authentication steps. It is off by default.
- Turning it on warns that kodi.log can include the Angel email and a one-time login code.

## [0.5.7] - 2026-11-01
- Require `script.module.auth0-ciam-client` 0.0.5.
- Test dependency is `auth0-ciam-client` tag `v0.2.2`.

## [0.5.6] - 2026-02-04
- Build system and CI/CD improvements, code quality enhancements, and documentation updates


## [0.5.5] - 2026-02-02
- Refactor CI workflows to eliminate ZIP building duplication and improve efficiency

## [0.5.4] - 2026-02-02
- Add multi-version Python testing (3.9-3.12) for forward compatibility and make addon checker warnings non-blocking

## [0.5.3] - 2026-02-02
- Update kodi-addon-builder to v0.3.7 and fix CI test path for Python 3.9 compatibility validation

## [0.5.2] - 2026-02-02
- Python 3.9 compatibility retrofit complete

## [0.5.1] - 2026-02-01
- build: fix CI by moving dev dependencies to uv dependency-groups format

## [0.5.0] - 2026-02-01
- Migrated to uv for modern Python dependency management, removed deprecated python-jose, extracted auth0-ciam-client, extensive code refactoring and cleanup, performance optimizations, and comprehensive testing improvements.

