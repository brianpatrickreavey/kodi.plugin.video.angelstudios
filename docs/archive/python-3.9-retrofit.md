# Python 3.9 Compatibility Retrofit Plan

## Overview
The CI pipeline is failing because the codebase uses Python 3.10+ syntax (`str | None` union types) while the CI environment runs Python 3.9.25. Since KODI targets Python 3.9+, we need to retrofit the codebase for 3.9 compatibility.

## Current Issue
- CI fails with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
- Local development uses Python 3.13, but CI uses 3.9
- Union syntax `str | None` is not supported in Python 3.9

## Action Items

### 1. Update Type Annotations (High Priority)
- [x] Replace `str | None` with `Optional[str]` in `angel_authentication.py` (line 78 and any others)
- [x] Search for all uses of `|` union syntax in the codebase and replace with `typing.Union` or `typing.Optional`
- [x] Add `from typing import Optional, Union` imports where needed
- [x] Update any other modern type syntax that might not be 3.9 compatible

### 2. Update CI Python Version (High Priority)
- [x] Change `.github/workflows/ci.yml` to use Python 3.9 instead of 3.13
- [x] Update the `uv python install 3.9` command to ensure consistency
- [x] Verify that all dependencies are compatible with Python 3.9

### 3. Update Local Development Environment (Medium Priority)
- [x] Update `pyproject.toml` to specify `requires-python = ">=3.9"` (if not already)
- [x] Consider adding a `pyproject.toml` `[tool.uv]` section to specify Python version preference (not supported by uv, skipped)
- [x] Update any local development scripts to use Python 3.9 (scripts use venv activation or python3, no changes needed)

### 4. Test Compatibility (High Priority)
- [x] Run tests locally with Python 3.9 to ensure they pass
- [x] Update CI to run on Python 3.9 and verify the pipeline passes
- [x] Check that all runtime dependencies work with Python 3.9

### 5. Documentation Updates (Low Priority)
- [x] Update README.md or development docs to specify Python 3.9+ requirement
- [x] Add notes about type annotation compatibility in contributing guidelines

### 6. Future Considerations (Low Priority)
- [x] Consider adding type checking configuration (pyright/mypy) that targets Python 3.9
- [x] Evaluate if any other modern Python features need to be downgraded for 3.9 compatibility

## Implementation Status
- [x] Plan documented
- [x] Type annotations updated (High Priority - Complete)
- [x] CI configuration updated (High Priority - Complete)
- [x] Tests passing on Python 3.9 (High Priority - Complete)
- [x] Local environment updated (Medium Priority - Complete)
- [x] Documentation updated (Low Priority - Complete)

## Completion Notes
All action items have been successfully implemented. The codebase now supports Python 3.9+ with proper type annotations, CI configuration, and documentation. Tests pass with 93.87% coverage.

## Notes
- Priority is given to fixing the immediate CI failure
- All changes should maintain backward compatibility
- The `uv` environment should use Python 3.9 to match KODI runtime