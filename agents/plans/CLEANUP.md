# Project Cleanup Plan

**Date:** January 15, 2026
**Status:** In progress – Phase 0 partially completed
**Owner:** Architecture & Product
**Audience:** Developer, Code Reviewer, QA

---

## Executive Summary

This cleanup plan addresses code organization, import strategy, caching patterns, authentication, UI consistency, error handling, logging, tests, and documentation accumulated during multi-feature development. The goal is to establish a clean, maintainable baseline before committing these features.

**Scope:**
- **In Scope:** Code readability, consistency, import normalization, redundancy removal, fixture clarity, docs alignment, minor performance wins (logging optimization).
- **Out of Scope (defer to next feature):** Session refresh token strategy, resumeWatching caching, integration tests, major architectural shifts.

**Risk Profile:**
- **Phase 0:** Zero risk (pure removals and constants extraction).
- **Phase 1:** Low-to-medium risk (refactors with comprehensive test coverage validation).
- **Phase 2:** Medium-to-high risk (behavioral changes; deferred post-commit).

**Timeline Estimate:**
- Phase 0: 1–2 hours
- Phase 1: 3–6 hours
- Phase 2: 8+ hours (deferred)
- **Total (Phases 0–1): ~6–8 hours**

**Success Criteria:**
1. All phases complete with 100% test coverage maintained via `make unittest-with-coverage`.
2. All code passes black + flake8 formatting.
3. Fixture refactoring improves readability (verified via code review).
4. No user-visible behavior changes (seamless UX preserved).
5. All docs updated; research docs archived.

---

## Current State Assessment

### Architecture Overview

**Component Map:**

| Component | File | Role | Dependencies |
|-----------|------|------|---|
| **Angel Interface (KODI-agnostic)** | `resources/lib/angel_interface.py` | GraphQL API calls, query/fragment loading, session management | `AngelStudioSession`, `requests` |
| **Angel Authentication** | `resources/lib/angel_authentication.py` | OAuth-like authentication, session persistence, validation | `requests`, pickle |
| **Kodi UI Interface** | `resources/lib/kodi_ui_interface.py` | Menu builders, list item creation, playback, caching, error dialogs | `xbmcplugin`, `xbmcgui`, `SimpleCache`, `AngelStudiosInterface` |
| **Kodi Utils** | `resources/lib/kodi_utils.py` | Logging, utility functions, Kodi integration helpers | `xbmc`, `xbmcaddon` |
| **Main Handler** | `plugin.video.angelstudios/__init__.py` | Plugin entry point, router, menu dispatch | `KodiUIInterface` |

**Data Flow:**
```
User Action (Kodi UI)
  → Router (__init__.py)
  → Menu Handler (kodi_ui_interface.py)
  → API Call (angel_interface.py)
  → Session Check (angel_authentication.py)
  → GraphQL Query + Fragment Loading
  → Response Parsing + Merge Logic
  → Cache Write (SimpleCache in UI layer)
  → List Item Creation + Infotag Population
  → Directory Rendering (xbmcplugin.addDirectoryItem)
  → endOfDirectory() (UI renders)
  → Deferred Cache Writes (post-render)
  → Return
```

### Key Patterns Established

1. **Caching:** SimpleCache in UI layer only; query/fragment caches in angel_interface (non-Kodi).
2. **Imports:** Mix of absolute (xbmc*) and relative; relative for internal lib modules ✅.
3. **Auth:** On-demand validation; no refresh token logic; session persisted via pickle.
4. **UI Patterns:** Menu builders fetch → render → endOfDirectory(); deferred writes post-render.
5. **Error Handling:** show_error() for user-visible; silent None returns for degraded cache misses.
6. **Logging:** KodiLogger wraps xbmc.log; stack introspection on every call; unredacted auth headers.
7. **Tests:** Unit tests mirrored to lib structure; fixtures in conftest.py; parametrization + mock patches; 100% coverage enforced.

### Known Issues (from Audit)

**Imports:**
- Unused imports in `kodi_ui_interface.py`, `angel_interface.py`, `angel_authentication.py`
- Duplicate imports in `test_kodi_ui_interface_menus.py`
- Optional addon detection uses correct pattern ✅

**Caching:**
- Hardcoded 1-hour TTL for projects menu (inconsistent with user settings)
- Query/fragment in-memory file caches have no eviction strategy (but small, low-impact); consider renaming to clarify they cache file contents, not data responses (e.g., `_query_file_cache`, `_fragment_file_cache`)
- resumeWatching results not cached (deferred to Phase 1)

**Auth:**
- No session refresh token logic; validation only on-demand
- Log headers/cookies unredacted (security risk)
- No request timeouts

**UI:**
- Long functions (75–100 lines): `projects_menu`, `episodes_menu`
- Repetitive list item creation scattered across menus
- Infotag field mapping uses if-chains (not parameterized)
- Hardcoded icons and constants scattered

**Logging:**
- KodiLogger stack introspection (9 frames) on every call (performance concern)
- GraphQL errors logged as empty `{}` (missing context)

**Tests & Fixtures:**
- Fixtures are functional but cryptic (mock setup hard to follow)
- Test data centralized but fixture chains could be clearer
- Multi-patch context managers correct ✅; documentation lacking

**Docs:**
- 5 research docs (`*_RESEARCH.md`, `*_ANALYSIS.md`) lack status markers
- `continue-watching.md` outdated
- Deprecated API references in code + docs

---

## Cleanup Phases

### Phase 0: Quick Wins *(Zero Risk)*

**Duration:** 1–2 hours
**Goal:** Remove cruft, establish constants, verify import strategy.

**Current Status:** Partially done
- ✅ 0.3 TTL constants added in kodi_ui_interface.py (defaults documented)
- ✅ 0.4 Research docs archived to docs/archive with README
- 🔶 0.1 Unused imports: pending cleanup (xbmcaddon still present in kodi_ui_interface.py; others need audit)
- 🔶 0.2 Duplicate MagicMock import in test_kodi_ui_interface_menus.py: pending
- 🔶 0.5 Relative-import audit: pending
- 🔶 0.6 Kodi-agnostic check for angel_interface.py / angel_authentication.py: pending
- 🔶 0.7 Flake8 nits: pending (unused vars, long line, unused imports noted)

**Test/coverage state:** `make unittest-with-coverage` passes (343/343, ~99% coverage). WIP snapshot committed at e556371.

#### 0.1 – Remove Unused Imports

**Files:**
- [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py) — remove unused `xbmcaddon`
- [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py) — remove unused `logging`, `sys`
- [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py) — remove unused `hashlib`

**Acceptance Criteria:**
- `pyright` reports no unused imports
- `flake8` reports no unused import violations
- Tests still pass at 100% coverage

#### 0.2 – Remove Duplicate Imports in Tests

**File:**
- [tests/unit/test_kodi_ui_interface_menus.py](../tests/unit/test_kodi_ui_interface_menus.py) — remove duplicate `MagicMock` import

**Acceptance Criteria:**
- Single import statement; no duplicates
- Tests pass

#### 0.3 – Extract Cache TTL Constants

**File:**
- [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**Changes:**
- Add module-level constants for cache TTL (referenced in user settings):
  ```python
  # Cache TTL defaults (in seconds)
  DEFAULT_CACHE_TTL_PROJECTS = 3600  # 1 hour (projects menu)
  DEFAULT_CACHE_TTL_EPISODES = 86400 * 3  # 72 hours
  DEFAULT_CACHE_TTL_PROJECT = 28800  # 8 hours (individual project)
  ```
- Replace hardcoded `3600` with `DEFAULT_CACHE_TTL_PROJECTS`
- Document how TTLs tie to user settings in docstrings

**Acceptance Criteria:**
- All cache operations use named constants
- No hardcoded TTL integers remain
- Cache behavior unchanged; tests pass

#### 0.4 – Archive Research Docs

**Files to Move:**
- [docs/IMAGE_PREFETCH_RESEARCH.md](../docs/IMAGE_PREFETCH_RESEARCH.md)
- [docs/IMAGE_PREFETCH_VERIFICATION_GUIDE.md](../docs/IMAGE_PREFETCH_VERIFICATION_GUIDE.md)
- [docs/INFOTAGS_OPTIMIZATION_RESEARCH.md](../docs/INFOTAGS_OPTIMIZATION_RESEARCH.md)
- [docs/TIMING_ANALYSIS.md](../docs/TIMING_ANALYSIS.md)
- [docs/TIMING_INSTRUMENTATION.md](../docs/TIMING_INSTRUMENTATION.md)

**Action:**
- Create `docs/archive/` directory
- Move all 5 research docs to `docs/archive/`
- Add `README.md` in archive explaining why (investigation notes, not actionable guidance)
- Update `.gitignore` to exclude archive if needed (or keep for history)

**Acceptance Criteria:**
- `docs/` contains only durable docs (data_structure, metadata-mapping, features/*, DEFERRED_CACHE_WRITES)
- Archive dir created with moved docs
- No broken references in active docs

#### 0.5 – Verify Relative Imports in Lib

**Scope:** Audit all imports in `resources/lib/**/*.py`

**Expected Pattern:**
- Internal lib modules: `from .angel_interface import AngelStudiosInterface` ✅
- External: `from requests import Session` ✅
- Kodi (xbmc*): `import xbmcplugin` ✅

**Action:** Run script or grep to verify no absolute imports of internal modules (e.g., no `from plugin.video.angelstudios.resources.lib...`).

**Acceptance Criteria:**
- All internal imports are relative
- No circular dependencies detected
- `pyright` reports no issues

#### 0.6 – Verify angel_interface.py and angel_authentication.py are KODI-Agnostic

**Scope:**
- [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)
- [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py)

**Expected (both files):**
- No `import xbmc*`, `import xbmcplugin`, `import xbmcgui`, `import xbmcaddon`
- No `SimpleCache` usage
- No Kodi-specific logic (safe to use in non-Kodi Python environments)
- Dependencies: only `requests`, `BeautifulSoup`, standard library

**Action:** Grep for xbmc imports + SimpleCache in both files.

**Acceptance Criteria:**
- Zero xbmc imports found in either file
- Zero SimpleCache usage found
- Both files can be imported in pure Python environment without errors
- Tests confirm (test fixtures don't inject Kodi mocks for these module tests)

#### 0.7 – Fix Flake8 Linting Issues (Zero-Risk Cleanup)

**Scope:** Address pre-existing linting issues that are formatting-only, not behavioral.

**Issues Fixed:**
- [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py):
  - Line 375: Remove unused `episode_count` variable (F841)
  - Line 472: Remove unused `cache_write_start` variable (F841)
  - Line 681: Break long log line to fit 120-char limit (E501)
- [tests/unit/test_angel_authentication.py](../tests/unit/test_angel_authentication.py):
  - Line 5: Remove unused `os` import (F401)
- [tests/unit/conftest.py](../tests/unit/conftest.py):
  - Line 62: Add `# noqa: E402` to delayed import (required for fixture setup)

**Acceptance Criteria:**
- All targeted flake8 errors resolved
- No new errors introduced
- 100% test coverage maintained
   - `kodi_xbmcplugin_mock()` — patches xbmcplugin methods
   - `kodi_xbmcgui_mock()` — patches xbmcgui methods (ListItem, Dialog)
   - `mock_session()` — returns MagicMock session with headers + cookies
   - `mock_angel_session()` — returns AngelStudioSession mock
   - `mock_simplecache()` — returns SimpleCache mock
4. **Group related fixtures** with comments (e.g., "## Kodi UI Mocks" section).
5. **Document fixture dependencies** (which fixtures depend on others).

**Example Before/After:**
```python
# BEFORE (conftest.py excerpt)
@pytest.fixture
def mock_addon():
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {...}
    return addon

# AFTER
@pytest.fixture
def kodi_addon_mock():
    """Mock Kodi addon with common settings (language, cache TTLs, etc.).

    Returns:
        MagicMock: Configured addon mock for unit tests.

    Note: Tests override getSetting() as needed for specific test cases.
    """
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {...}
    return addon
```

**Acceptance Criteria:**
- Every fixture has a docstring (purpose + returns)
- Fixture names are descriptive (prefer 3–5 words)
- Tests still pass (mock behavior unchanged)
- Code review confirms "hard to follow fixtures" complaint resolved

#### 1.2 – Redact Auth Logs in angel_authentication.py

**File:** [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py)

**Current Issue:**
Lines 122–125 (approx.) log unredacted session headers and cookies, exposing potential credentials.

**Action:**
Create helper function to sanitize headers before logging:
```python
def _sanitize_headers_for_logging(headers):
    """Remove sensitive headers (Authorization, Cookie) before logging."""
    safe_headers = {
        k: v for k, v in headers.items()
        if k.lower() not in ("authorization", "cookie", "x-api-key")
    }
    return safe_headers
```

Replace all `self.log.debug(f"Headers: {self.session.headers}")` with `self.log.debug(f"Headers: {_sanitize_headers_for_logging(self.session.headers)}")`.

**Acceptance Criteria:**
- No unredacted Authorization or Cookie headers logged
- `self.log.debug()` calls for headers use sanitize function
- Tests confirm (check test logs for absence of credentials)

#### 1.3 – Improve GraphQL Error Logging in angel_interface.py

**File:** [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)

**Current Issue:**
GraphQL errors return empty `{}` without logging details. Makes debugging hard.

**Action:**
In `_graphql_query()`, enhance error logging:
```python
if "errors" in result:
    # Log full error details for debugging
    self.log.error(f"GraphQL errors for operation '{operation}':")
    for error in result.get("errors", []):
        if isinstance(error, dict):
            self.log.error(f"  - {error.get('message', 'Unknown error')}")
            if "extensions" in error:
                self.log.debug(f"    Extensions: {error['extensions']}")
        else:
            self.log.error(f"  - {error}")
    data = {}
```

**Acceptance Criteria:**
- GraphQL error responses logged with full details (message + extensions)
- Operation name included in log
- Tests mock GraphQL errors and verify logging calls

#### 1.4 – Extract ListItem Builder Abstraction

**File:** [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**Current Issue:**
List item creation scattered across `projects_menu()`, `seasons_menu()`, `episodes_menu()`, `continue_watching_menu()`. Duplication in artwork, infotags, progress bar logic.

**Strategy:**
1. Create helper class or method: `_build_list_item_for_content(content, content_type, **options)`
2. Centralize:
   - Icon/artwork resolution
   - Infotag population
   - Progress bar injection
   - Context menu creation
3. Parameterize options: `overlay_progress=True`, `include_resume=True`, etc.

**Example Structure:**
```python
def _build_list_item_for_content(self, content, content_type, **options):
    """
    Build a Kodi ListItem for content (episode, project, etc.).

    Args:
        content (dict): Content data (from API)
        content_type (str): 'episode', 'project', 'season', etc.
        overlay_progress (bool): Whether to add resume point overlay
        include_resume (bool): Whether to populate watchPosition

    Returns:
        xbmcgui.ListItem: Configured list item ready for addDirectoryItem()
    """
    list_item = xbmcgui.ListItem(label=content.get("name", "Unknown"))

    # Set artwork
    artwork = self._resolve_artwork(content, content_type)
    list_item.setArt(artwork)

    # Set infotags
    self._process_attributes_to_infotags(list_item, content, content_type)

    # Add progress bar overlay if requested
    if options.get("overlay_progress"):
        self._apply_progress_bar(list_item, content)

    return list_item
```

Use in menus:
```python
def episodes_menu(self, ...):
    # ... fetch episodes ...
    for episode in episodes:
        list_item = self._build_list_item_for_content(
            episode,
            "episode",
            overlay_progress=True
        )
        # ... add to directory ...
```

**Acceptance Criteria:**
- Single `_build_list_item_for_content()` method used across all menus
- No duplication in list item creation
- Tests parametrize over content types
- 100% test coverage maintained

#### 1.5 – Review Infotag Field Mapping (DO NOT REFACTOR TO LOOPS)

**File:** [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**IMPORTANT:** Previous analysis (docs/archive/INFOTAGS_OPTIMIZATION_RESEARCH.md) shows the current if-chain approach is **already optimized** and provides **80%+ speedup** over the old generic-loop approach. The optimization came from:

1. **Lazy initialization** of expensive Kodi C++ calls (getVideoInfoTag, setArt, etc.)
2. **Intelligent prioritization** (e.g., portrait stills > title images > discovery posters)
3. **Batching** Cloudinary URL building and art dictionary assembly
4. **Conditional processing** that avoids redundant operations

**Current Issue (Minor):**
- Extensive debug logging (lines prefixed with `[ART]`) adds overhead in production; logging can be optimized
- Some redundant comments that could be consolidated
- Structure could be documented more clearly for maintainability

**Strategy:**
1. Review current `_process_attributes_to_infotags()` implementation (lines ~1550-1700) to understand optimizations
2. **KEEP the if-chain structure** (performance-critical)
3. **Reduce debug logging** in production by using fewer log levels or conditional logging
4. **Add comments** explaining WHY this structure is optimized (architectural decisions, not performance tricks)
5. Verify no new redundancies introduced in recent changes

**Action:**
- Audit current function for any new redundancies or dead code
- Document the optimization strategy in code comments
- Consider extracting logging level to a constant or debug flag

**Acceptance Criteria:**
- Current if-chain structure preserved (performance confirmed)
- Unnecessary debug logging reduced (production log volume lower)
- Code comments explain optimization rationale
- 100% test coverage maintained
- Rendering performance unchanged or improved

#### 1.6 – Consolidate Progress Bar Logic

**File:** [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**Current Issue:**
`_apply_progress_bar()` called in multiple menus; logic may be repeated or inconsistent.

**Action:**
1. Ensure single `_apply_progress_bar()` implementation
2. Document expected input format (watchPosition dict with position, total, % fields)
3. Use in `_build_list_item_for_content()` with `overlay_progress=True` option

**Acceptance Criteria:**
- Progress bar applied consistently across all menus
- Tests verify progress bar presence/absence based on options
- No code duplication

#### 1.7 – Update continue-watching.md

**File:** [docs/features/continue-watching.md](../docs/features/continue-watching.md)

**Action:**
1. Verify implementation matches docs (feature state, query structure, merge logic)
2. Update example data if outdated
3. Add reference to deferred writes pattern

**Acceptance Criteria:**
- Docs match current implementation
- Examples are accurate
- No TODOs in feature doc (moved to plan if needed)

#### 1.8 – Remove Deprecated API References

**Files:**
- [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py) — search for deprecated methods
- [docs/data_structure.md](../docs/data_structure.md) — update/remove deprecated refs

**Action:**
1. Identify any `# TODO` or `@deprecated` markers in code
2. Either implement or remove
3. Update docs to reflect current API surface

**Acceptance Criteria:**
- No deprecated references in active code
- Docs reflect only current API

---

### Phase 2: Deeper Improvements *(Higher Risk — Deferred to Next Feature)*

This phase introduces behavioral changes and is **deferred post-commit**. Documented here for future reference.

#### 2.1 – Implement Session Refresh Token Strategy

**Status:** DEFERRED

**Scope:** [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py)

**Current:** Session validated on-demand; full re-auth if invalid.
**Proposed:** Refresh token logic; proactive refresh before expiry.

**Acceptance Criteria:** TBD in next feature planning.

#### 2.2 – Add Integration Tests

**Status:** DEFERRED

**Scope:** `tests/integration/` (new)

**Proposed:** Tests that exercise full flow (API + UI + caching).

**Acceptance Criteria:** TBD in next feature planning.

#### 2.4 – Optimize KodiLogger Performance

**Status:** DEFERRED

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_utils.py](../plugin.video.angelstudios/resources/lib/kodi_utils.py) (KodiLogger)

**Current:** Stack introspection on every log call (9 frames checked).
**Proposed:** Cache frame info or use faster caller detection.

**Acceptance Criteria:** TBD in next feature planning.

---

## Test Strategy & Validation

### Unit Tests (Phases 0–1)

**Requirement:** 100% coverage via `make unittest-with-coverage`

**Approach:**
1. **After each phase**, run full test suite to confirm coverage maintained
2. **Phase 1 changes** (refactoring): Ensure tests don't change behavior (they verify behavior)
3. **New fixtures/helpers** (1.1): Add unit tests for fixture composition
4. **New abstractions** (1.4, 1.5): Add parametrized tests for all content types

**Commands:**
```bash
make unittest-with-coverage
```

Expected output: `100% coverage` or coverage report highlighting any gaps (should be zero gaps).

### Code Quality (Phases 0–1)

**Commands:**
```bash
make lint      # pyright + flake8 + black check
black --line-length=120 plugin.video.angelstudios/ tests/
flake8 plugin.video.angelstudios/ tests/ --max-line-length=120
pyright
```

Expected: Zero errors; zero warnings; consistent formatting.

### Manual Verification

After Phase 1, **code review checklist:**
- [ ] All imports relative (lib); absolute (external); imports reduced
- [ ] Cache TTLs use named constants
- [ ] angel_interface.py has zero xbmc/Kodi imports
- [ ] Fixtures in conftest.py have clear docstrings
- [ ] Auth logs sanitized (no credentials)
- [ ] GraphQL errors logged with details
- [ ] List items built via single abstraction
- [ ] Infotag mapping uses loop, not if-chains
- [ ] progress bar logic consolidated
- [ ] Docs updated/archived

---

## Configuration Updates

### Update Makefile

**File:** [Makefile](../Makefile)

**Add targets:**
```makefile
.PHONY: format
format:
	black --line-length=120 plugin.video.angelstudios/ tests/

.PHONY: lint-check
lint-check:
	pyright plugin.video.angelstudios/ tests/
	flake8 plugin.video.angelstudios/ tests/ --max-line-length=120
	black --check --line-length=120 plugin.video.angelstudios/ tests/

.PHONY: format-and-lint
format-and-lint: format lint-check

.PHONY: test-timing
test-timing:
	@echo "Running tests with timing instrumentation..."
	pytest tests/unit/ -v --tb=short
```

**Update existing targets** (if needed):
- `lint`: Add `black --check` to verify formatting without modifying
- `unittest-with-coverage`: Confirm output format (term-missing)

### Update .gitignore

**Add (if not already present):**
```
# Test artifacts
test_cache/
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/settings.json

# Docs archive (optional; keep for reference)
# docs/archive/

# Build/dist
*.egg-info/
dist/
build/
```

### Create pytest.ini

**File:** `pytest.ini` (project root)

```ini
[pytest]
testpaths = tests/unit
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
# Timing output for performance monitoring
markers =
    timing: marks tests related to timing instrumentation
```

### Extract Flake8 Config

**File:** `.flake8` (project root)

```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,build,dist,.venv
ignore = E203, W503, E501  # Line length handled by black
per-file-ignores =
    __init__.py: F401
    tests/**/*.py: F405
```

---

## Fixture Refactoring Details

### Current Fixture Structure (Simplified)

```python
# conftest.py (current)
@pytest.fixture
def addon():
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {...}
    return addon

@pytest.fixture
def handle():
    return 1

@pytest.fixture
def mock_kodi_ui(addon, handle):
    with patch('xbmcplugin.setResolvedUrl') as ...:
        with patch('xbmcgui.ListItem') as ...:
            # ... many patches ...
            pass
```

### Proposed Fixture Structure (Phase 1.1)

```python
# conftest.py (refactored)

## ============================================================================
## Kodi UI Mocks
## ============================================================================

@pytest.fixture
def kodi_addon_mock():
    """Mock Kodi addon with common settings.

    Returns:
        MagicMock: Addon mock with getSetting() configured for cache TTLs,
                   language, etc. Tests override as needed.
    """
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {
        "cache_ttl_projects": "3600",
        # ... other settings ...
    }.get(key, "")
    addon.getAddonInfo.side_effect = lambda key: {
        "path": "/fake/addon/path",
    }.get(key, "")
    return addon

@pytest.fixture
def kodi_handle():
    """Kodi plugin handle (typically integer 1)."""
    return 1

@pytest.fixture
def kodi_xbmcplugin_mock():
    """Mock xbmcplugin module with common methods.

    Yields:
        MagicMock: Patched xbmcplugin module.
    """
    with patch('xbmcplugin.addDirectoryItem') as mock_add, \
         patch('xbmcplugin.endOfDirectory') as mock_end, \
         patch('xbmcplugin.setResolvedUrl') as mock_resolve:
        yield {
            'addDirectoryItem': mock_add,
            'endOfDirectory': mock_end,
            'setResolvedUrl': mock_resolve,
        }

@pytest.fixture
def kodi_xbmcgui_mock():
    """Mock xbmcgui module (ListItem, Dialog, etc).

    Yields:
        dict: Named mocks for ListItem, Dialog classes.
    """
    with patch('xbmcgui.ListItem') as mock_listitem, \
         patch('xbmcgui.Dialog') as mock_dialog:
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()
        yield {
            'ListItem': mock_listitem,
            'Dialog': mock_dialog,
        }

## ============================================================================
## Session & API Mocks
## ============================================================================

@pytest.fixture
def mock_http_session():
    """Mock requests.Session for HTTP calls.

    Returns:
        MagicMock: Session with post(), get() methods pre-configured.
    """
    session = MagicMock()
    session.headers = {"Authorization": "Bearer fake_token"}
    session.cookies = {}
    session.post.return_value.json.return_value = {}
    session.post.return_value.status_code = 200
    return session

@pytest.fixture
def mock_angel_studio_session(mock_http_session):
    """Mock AngelStudioSession with authenticated session.

    Returns:
        MagicMock: AngelStudioSession configured with mock HTTP session.
    """
    angel_session = MagicMock()
    angel_session.get_session.return_value = mock_http_session
    angel_session._validate_session.return_value = True
    angel_session.session_valid = True
    return angel_session

## ============================================================================
## Cache Mocks
## ============================================================================

@pytest.fixture
def mock_simplecache():
    """Mock SimpleCache for testing cache operations.

    Returns:
        MagicMock: SimpleCache with get() and set() methods.

    Note: Tests can override side_effect to simulate cache hits/misses.
    """
    cache = MagicMock()
    cache.get.return_value = None  # Default: miss
    cache.set.return_value = True
    return cache

## ============================================================================
## Composed Fixtures (convenience)
## ============================================================================

@pytest.fixture
def kodi_ui_interface(kodi_addon_mock, kodi_handle, kodi_xbmcplugin_mock,
                      kodi_xbmcgui_mock, mock_simplecache, mock_angel_studio_session):
    """Fully configured KodiUIInterface for testing.

    Patches Kodi modules + cache + session, then yields ready-to-use UI interface.

    Returns:
        KodiUIInterface: Configured for unit testing.
    """
    with patch('xbmcaddon.Addon', return_value=kodi_addon_mock), \
         patch('xbmcplugin.setResolvedUrl') as _, \
         patch('xbmcgui.ListItem') as mock_li, \
         patch('simplecache.SimpleCache', return_value=mock_simplecache):
        # Configure ListItem to return proper mock
        mock_li.return_value.getVideoInfoTag.return_value = MagicMock()

        # Create UI interface
        ui = KodiUIInterface(handle=kodi_handle)
        ui.angel_interface = MagicMock()  # Override with mock
        ui.angel_interface.get_projects.return_value = []

        return ui
```

**Benefits:**
1. **Clear purpose**: Each fixture docstring explains what it mocks and why.
2. **Composable**: Small, single-purpose fixtures composed into larger ones.
3. **Reusable**: Tests use `mock_simplecache` or `kodi_xbmcplugin_mock` independently.
4. **Maintainable**: Changes to Kodi API need updates only in relevant fixture.

---

## Docs Strategy

### Research Docs → Archive

**Move to `docs/archive/`:**
- IMAGE_PREFETCH_RESEARCH.md
- IMAGE_PREFETCH_VERIFICATION_GUIDE.md
- INFOTAGS_OPTIMIZATION_RESEARCH.md
- TIMING_ANALYSIS.md
- TIMING_INSTRUMENTATION.md

**Rationale:** Investigation and exploration; not actionable post-implementation.
**Add:** `docs/archive/README.md` explaining why archived.

### Durable Docs (Update/Keep)

| File | Action |
|------|--------|
| [data_structure.md](../docs/data_structure.md) | Keep as-is (current) ✅ |
| [metadata-mapping.md](../docs/metadata-mapping.md) | Keep as-is (current) ✅ |
| [DEFERRED_CACHE_WRITES.md](../docs/DEFERRED_CACHE_WRITES.md) | **Update**: Remove SimpleCache references; note caching happens in UI layer |
| [features/continue-watching.md](../docs/features/continue-watching.md) | **Update**: Verify implementation; refresh examples |
| [.github/copilot-instructions.md](../.github/copilot-instructions.md) | **Review**: Ensure architecture guidance matches cleaned-up code |

### New Docs (Optional)

Consider adding in future (not in this cleanup):
- `docs/ARCHITECTURE.md` — High-level overview (data flow, components, key patterns)
- `docs/TESTING.md` — Unit test strategy, fixtures, coverage approach
- `docs/CACHING.md` — Consolidated caching guide (cache keys, TTLs, invalidation)

---

## Timing Capture (Performance Baseline)

**Goal:** Establish pre-cleanup menu performance baseline for later measurement.

**Implementation:**
Add timing instrumentation to key menus in Phase 1 (leveraging existing pattern in DEFERRED_CACHE_WRITES.md):

```python
def projects_menu(self, ...):
    """Fetch and render projects menu with timing instrumentation."""
    start_time = time.perf_counter()

    # ... fetch projects ...
    fetch_time = (time.perf_counter() - start_time) * 1000

    # ... render items ...
    render_time = (time.perf_counter() - (start_time + fetch_time / 1000)) * 1000

    xbmcplugin.endOfDirectory(self.handle)
    self.log.info(
        f"[TIMING] projects_menu COMPLETED in {(time.perf_counter() - start_time) * 1000:.1f}ms "
        f"(fetch: {fetch_time:.1f}ms, render: {render_time:.1f}ms, cache_write: deferred)"
    )

    # ... deferred cache writes ...
```

**Baseline Commands:**
```bash
# Run menu tests and grep for timing logs
pytest tests/unit/test_kodi_ui_interface_menus.py -v -s | grep TIMING
```

**Post-Cleanup Comparison:**
Timing logs from Phase 1 complete become baseline. Phase 2 (deferred) can measure impact of session refresh / caching changes.

---

## Progress Tracking

### Phase 0 Checklist

- [ ] 0.1 – Remove unused imports (3 files)
  - [ ] kodi_ui_interface.py
  - [ ] angel_interface.py
  - [ ] angel_authentication.py
  - [ ] Tests pass; pyright/flake8 clean
- [ ] 0.2 – Remove duplicate imports (tests)
  - [ ] test_kodi_ui_interface_menus.py
- [ ] 0.3 – Extract cache TTL constants
  - [ ] kodi_ui_interface.py (module-level constants)
  - [ ] Update all hardcoded TTLs
  - [ ] Tests pass
- [ ] 0.4 – Archive research docs
  - [ ] Create `docs/archive/`
  - [ ] Move 5 docs
  - [ ] Add README
- [ ] 0.5 – Verify relative imports
  - [ ] All internal lib imports are relative
  - [ ] No circular dependencies
  - [ ] pyright clean
- [ ] 0.6 – Verify angel_interface.py and angel_authentication.py are KODI-agnostic
  - [ ] Zero xbmc imports in both files
  - [ ] Zero SimpleCache usage in both files
  - [ ] Pure Python import check for both
- [ ] 0.7 – Fix flake8 linting issues (zero-risk cleanup)
  - [ ] Remove unused `episode_count` variable in kodi_ui_interface.py
  - [ ] Remove unused `cache_write_start` variable in kodi_ui_interface.py
  - [ ] Fix long line (681) in kodi_ui_interface.py
  - [ ] Remove unused `os` import in test_angel_authentication.py
  - [ ] Add noqa comment to delayed import in conftest.py
  - [ ] All targeted errors resolved
- [ ] **Phase 0 Complete**: Run `make unittest-with-coverage` → expect 100% coverage
- [ ] **Phase 0 Complete**: Run `make lint` → expect targeted errors resolved

### Phase 1 Checklist

- [ ] 1.1 – Refactor test fixtures (conftest.py)
  - [ ] All fixtures have docstrings
  - [ ] Fixture names descriptive
  - [ ] Composed fixtures documented
  - [ ] Tests pass
- [ ] 1.2 – Redact auth logs
  - [ ] Create `_sanitize_headers_for_logging()`
  - [ ] Update all header log calls
  - [ ] No credentials in logs
- [ ] 1.3 – Improve GraphQL error logging
  - [ ] Error messages logged with details
  - [ ] Operation name in logs
  - [ ] Tests verify logging
- [ ] 1.4 – Extract ListItem builder
  - [ ] Single `_build_list_item_for_content()` method
  - [ ] All menus use builder
  - [ ] No duplication in list item creation
- [ ] 1.5 – Refactor infotag field mapping
  - [ ] `CONTENT_INFOTAG_MAPPING` constant
  - [ ] Loop replaces if-chains
  - [ ] Type checking in loop
  - [ ] Tests parametrized for all content types
- [ ] 1.6 – Consolidate progress bar logic
  - [ ] Single `_apply_progress_bar()` implementation
  - [ ] Used in `_build_list_item_for_content()`
  - [ ] Consistent behavior across menus
- [ ] 1.7 – Update continue-watching.md
  - [ ] Docs match implementation
  - [ ] Examples accurate
- [ ] 1.8 – Remove deprecated API references
  - [ ] No `@deprecated` or stale TODOs
  - [ ] Docs updated
- [ ] **Phase 1 Complete**: Run `make unittest-with-coverage` → expect 100% coverage
- [ ] **Phase 1 Complete**: Run `make format-and-lint` → expect zero errors
- [ ] **Phase 1 Complete**: Code review sign-off

---

## Risk Mitigation

### Phase 0 Risks: **Minimal**

**Risk:** Unused import removal breaks static analysis or imports elsewhere.
**Mitigation:** Run pyright + full test suite after each removal.

**Risk:** Cache TTL constant extraction affects behavior.
**Mitigation:** Replace hardcoded values exactly; test coverage catches any mismatches.

### Phase 1 Risks: **Medium**

**Risk:** Fixture refactoring changes mock behavior; tests pass but behavior diverges.
**Mitigation:** Tests remain unchanged (behavior verification); only fixtures refactored; run full suite.

**Risk:** ListItem builder abstraction introduces bugs in list rendering.
**Mitigation:** Parametrize tests over all content types (episode, project, season, etc.); verify artwork/infotags per type.

**Risk:** Infotag mapping loop misses edge cases (type coercion, None values).
**Mitigation:** Add type checking in loop; handle None gracefully; log warnings; tests cover edge cases.

### Phase 2 Risks: **Higher** (deferred)

Session refresh / resumeWatching caching could affect auth flow or cache invalidation. Deferred to next feature for dedicated testing.

---

## Post-Cleanup Checklist (Final)

**Before Commit:**
- [ ] All phases complete (0–1)
- [ ] `make unittest-with-coverage` → 100% coverage
- [ ] `make format-and-lint` → zero errors
- [ ] Code review approved
- [ ] Docs updated/archived
- [ ] .gitignore updated
- [ ] Makefile targets added
- [ ] pytest.ini created
- [ ] .flake8 config created
- [ ] Timing baseline captured

**Commit Message:**
```
feat: cleanup codebase before feature commit

- Phase 0: Remove unused imports, extract cache TTL constants, archive research docs
- Phase 1: Refactor fixtures for clarity, redact auth logs, improve GraphQL error logging,
  extract ListItem builder, refactor infotag mapping, consolidate progress bar logic,
  update continue-watching docs, remove deprecated API references
- Add Makefile targets: format, lint-check, format-and-lint
- Add pytest.ini and .flake8 for linting config
- Update .gitignore for test artifacts
- 100% test coverage maintained throughout

Refs: #cleanup
```

---

## Appendix: File Change Summary

### Phase 0 Changes

| File | Change Type | Scope |
|------|---|---|
| `resources/lib/kodi_ui_interface.py` | Remove import | 1 line |
| `resources/lib/angel_interface.py` | Remove imports + Add constants | 2 removals + ~5 new lines |
| `resources/lib/angel_authentication.py` | Remove import | 1 line |
| `tests/unit/test_kodi_ui_interface_menus.py` | Remove import | 1 line |
| `docs/archive/` | Move 5 docs | New directory |
| `docs/archive/README.md` | Create | ~20 lines |

### Phase 1 Changes

| File | Change Type | Scope |
|------|---|---|
| `tests/unit/conftest.py` | Refactor fixtures | ~150 line diff |
| `resources/lib/angel_authentication.py` | Add sanitize function + update calls | ~30 lines |
| `resources/lib/angel_interface.py` | Enhance error logging | ~10 lines |
| `resources/lib/kodi_ui_interface.py` | Extract builder + field mapping + constants + cache wrapper | ~120 lines refactored |
| `docs/DEFERRED_CACHE_WRITES.md` | Update caching notes | ~10 line updates |
| `docs/features/continue-watching.md` | Verify + update examples | ~20 line updates |
| `Makefile` | Add targets | ~15 new lines |
| `.flake8` | Create | ~10 lines |
| `pytest.ini` | Create | ~10 lines |
| `.gitignore` | Update | ~5 lines |

---

**Document Status:** Ready for Review
**Next Step:** Architect/Product approval → Implementation begins with Phase 0
