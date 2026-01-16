# Project Cleanup Plan (Grok Version)

**Date:** January 16, 2026
**Status:** Active – Phase 0 Implementation
**Owner:** Architecture & Product
**Audience:** Developer, Code Reviewer, QA

---

## Executive Summary

This cleanup plan focuses on Phase 0 quick wins to establish a clean baseline before committing features. Scope reduced to independent, granular steps with full test validation and git commits after each. All tests must pass; pause between steps for review.

**Scope:**
- **In Scope:** Remove unused imports, duplicates, verify imports/Kodi-agnostic, fix lint issues.
- **Out of Scope:** Phase 1+ refactors (deferred).

**Risk Profile:** Zero risk (pure removals/verifications).

**Timeline Estimate:** 1–2 hours

**Success Criteria:**
1. All steps complete + validated.
2. 100% test coverage maintained.
3. Code passes black + flake8.
4. No behavioral changes.

---

## Implementation Steps

1. **Investigate archive docs**: Confirm docs/archive/ exists with moved files, no action needed.
   - Status: Completed (already done).

2. **Remove duplicate MagicMock in test_kodi_ui_interface_menus.py**: Audit, remove duplicate, validate, commit "chore(cleanup): remove duplicate MagicMock import in test_kodi_ui_interface_menus.py (step 2)".

3. **Verify relative imports in lib**: Grep for absolute internal imports, fix if any, validate with make lint, commit "chore(cleanup): verify relative imports in lib (step 3)".

4. **Verify Kodi-agnostic angel_interface.py**: Grep for xbmc/SimpleCache, test pure import, validate, commit "chore(cleanup): verify angel_interface.py is Kodi-agnostic (step 4)".

5. **Verify Kodi-agnostic angel_authentication.py**: Grep, test import, validate, commit "chore(cleanup): verify angel_authentication.py is Kodi-agnostic (step 5)".

6. **Fix unused vars in kodi_ui_interface.py**: Remove episode_count/cache_write_start, validate, commit "chore(cleanup): remove unused vars in kodi_ui_interface.py (step 6)".

7. **Fix long line in kodi_ui_interface.py**: Break line 681, validate, commit "chore(cleanup): fix long line in kodi_ui_interface.py (step 7)".

8. **Fix unused os import in test_angel_authentication.py**: Remove, validate, commit "chore(cleanup): remove unused os import in test_angel_authentication.py (step 8)".

9. **Fix delayed import in conftest.py**: Add noqa, validate, commit "chore(cleanup): add noqa to delayed import in conftest.py (step 9)".

10. **Remove unused imports (deferred)**: Use flake8 to identify, remove all unused imports across files, validate, commit "chore(cleanup): remove all unused imports identified by flake8 (step 10)".

11. **Final validation**: Run all commands, tag phase-0-complete with "Phase 0 complete: all quick wins applied".

---

## Validation Commands

- `make unittest-with-coverage`
- `make black-check`
- `make black`
- `make flake8`
- `make lint`

---

## Progress Log

- Step 1: Completed (investigated).
- Step 2: Completed (no duplicate found).
- Step 3: Completed (verified absolute imports are correct).
- Step 4: Completed (verified Kodi-agnostic).

Author: Grok
Last Updated: January 16, 2026
