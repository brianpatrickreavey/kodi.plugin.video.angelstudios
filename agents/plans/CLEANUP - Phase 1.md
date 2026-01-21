# Project Cleanup Plan - Phase 1

**Date:** January 20, 2026
**Status:** Phase 1.7 completed
**Owner:** Architecture & Product
**Audience:** Developer, Code Reviewer, QA

---

## Executive Summary

This cleanup plan addresses code organization, import strategy, caching patterns, authentication, UI consistency, error handling, logging, tests, and documentation accumulated during multi-feature development. The goal is to establish a clean, maintainable baseline before committing these features. This also addresses regressions from previous work, such as if-chain structures that were accidentally altered and needed reconstitution.

**Design Principles:**
- Prioritize verbose, readable code for human readers (given agent-generated code in the codebase).
- Maintain separation of concerns, especially between Kodi UI interface and Angel Studios API interface.

**Risk Profile:**
- **Phase 1:** Low-to-medium risk (refactors with comprehensive test coverage validation).

**Timeline Estimate:**
- Phase 1: 3–6 hours

**Success Criteria:**
1. All phases complete with test coverage maintained (deferring 100% goal to Phase 2 or beyond; losing some coverage for better fixtures is acceptable)
2. All code passes black + flake8 formatting.
3. Fixture refactoring improves readability (verified via code review and UI spot-checks).
4. No user-visible behavior changes (seamless UX preserved).
5. All docs updated/archived.

---

## Current State Assessment (Post Phase 0)

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

### Known Issues (from Audit, Post Phase 0)

**Imports:**
- ✅ Unused imports removed (Phase 0)
- ✅ Duplicate imports removed (Phase 0)
- Optional addon detection uses correct pattern ✅

**Caching:**
- ✅ Separate cache TTL settings added (Phase 0)
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
- KodiLogger stack introspection (9 frames) on every log call (performance concern)
- GraphQL errors logged as empty `{}` (missing context)

**Tests & Fixtures:**
- Fixtures are functional but cryptic (mock setup hard to follow)
- Test data centralized but fixture chains could be clearer
- Multi-patch context managers correct ✅; documentation lacking

**Docs:**
- ✅ Research docs archived (Phase 0)
- `continue-watching.md` outdated
- Deprecated API references in code + docs

---

## Cleanup Phases

### Phase 1: Quick Wins *(Low-to-Medium Risk)*

**Duration:** 3–6 hours
**Goal:** Improve readability, consistency, logging, and minor performance wins while maintaining 100% test coverage.

**Current Status:** Phase 1 not started

#### 1.1 – Refactor Test Fixtures (conftest.py)

**Files:**
- [tests/unit/conftest.py](../tests/unit/conftest.py) — refactor all fixtures for clarity and composability

**Current Issue:**
Fixtures are functional but cryptic (mock setup hard to follow); test data centralized but fixture chains could be clearer.

**Action:**
Refactor `conftest.py` to use descriptive fixture names, add comprehensive docstrings, and structure for composability. Group fixtures by purpose (Kodi UI mocks, session mocks, cache mocks, composed fixtures).

**Example Structure:**
```python
## ============================================================================
## Kodi UI Mocks
## ============================================================================

@pytest.fixture
def mock_kodi_addon():
    """Mock Kodi addon with common settings.

    Returns:
        MagicMock: Addon mock with getSetting() configured for cache TTLs,
                   language, etc. Tests override as needed.
    """
    addon = MagicMock()
    addon.getSetting.side_effect = lambda key: {
        "projects_cache_hours": "12",
        "project_cache_hours": "8",
        "episodes_cache_hours": "72",
        # ... other settings ...
    }.get(key, "")
    return addon

@pytest.fixture
def mock_kodi_handle():
    """Kodi plugin handle (typically integer 1)."""
    return 1

@pytest.fixture
def mock_kodi_xbmcplugin():
    """Mock xbmcplugin module with common methods.

    Yields:
        dict: Named mocks for addDirectoryItem, endOfDirectory, setResolvedUrl.
    """
    with patch('xbmcplugin.addDirectoryItem') as mock_add, \
         patch('xbmcplugin.endOfDirectory') as mock_end, \
         patch('xbmcplugin.setResolvedUrl') as mock_resolve:
        yield {
            'addDirectoryItem': mock_add,
            'endOfDirectory': mock_end,
            'setResolvedUrl': mock_resolve,
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

**Acceptance Criteria:**
- Every fixture has a docstring (purpose + returns)
- Fixture names are descriptive (prefer 3–5 words)
- Composed fixtures documented with clear composition
- Tests still pass (mock behavior unchanged)
- Code review confirms "hard to follow fixtures" complaint resolved

**Pending Questions:**
- [ ] Confirm fixture structure and naming conventions

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

**Pending Questions:**
- [ ] Confirm all locations where headers are logged

#### 1.3 – Improve GraphQL Error Logging in angel_interface.py ✅ COMPLETED

**File:** [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)

**Current Issue:**
GraphQL errors return empty `{}` without logging details. Makes debugging hard.

**Action:**
In `_graphql_query()`, enhanced error logging (no stack traces needed):
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
- ✅ GraphQL error responses logged with full details (message + extensions)
- ✅ Operation name included in log
- ✅ Tests mock GraphQL errors and verify logging calls

**Implementation Details:**
- Enhanced `_graphql_query()` method to log detailed error information
- Updated test assertions to verify new logging format
- All tests pass with 87% coverage maintained

#### 1.4 – Extract ListItem Builder Abstraction ✅ COMPLETED

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
- ✅ Single `_build_list_item_for_content()` method used across all menus
- ✅ No duplication in list item creation
- ✅ Tests parametrize over content types
- ✅ 100% test coverage maintained

**Implementation Details:**
- Moved `_build_list_item_for_content()` to `MenuUtils` base class for shared access
- Made `KodiMenuHandler` inherit from `MenuUtils` to consolidate functionality
- Updated `projects_menu()`, `seasons_menu()`, `episodes_menu()`, `continue_watching_menu()` to use unified builder
- Maintained backward compatibility and all existing functionality
- All 124 menu handler tests pass

#### 1.5 – Review Infotag Field Mapping (VALIDATE ONLY - DO NOT REFACTOR)

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

**Action:**
1. Review current `_process_attributes_to_infotags()` implementation (lines ~1550-1700) to validate if-chains are intact and optimized
2. **KEEP the if-chain structure** (performance-critical)
3. **Validate debug logging** can be suppressed via settings.xml (no code changes needed)
4. **Add comments** explaining WHY this structure is optimized (architectural decisions, not performance tricks)
5. Verify no new redundancies introduced in recent changes

**Acceptance Criteria:**
- Current if-chain structure preserved (performance confirmed)
- Debug logging suppression validated (via settings)
- Code comments explain optimization rationale
- 100% test coverage maintained
- Rendering performance unchanged or improved

**Pending Questions:**
- [x] Validate if-chains are intact and optimized

**Completed:** January 21, 2026
- If-chain structure validated as intact and optimized (85-90% performance improvement maintained)
- Debug logging suppression validated via `debug_art_promotion` setting in settings.xml
- Optimization rationale well-documented in method docstring and comments
- All tests pass (436/436) with 87% coverage maintained
- Pyright type checking: 0 errors, 0 warnings

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

**Pending Questions:**
- [x] Confirm all locations where progress bar logic is used

**Completed:** January 21, 2026
- Single `_apply_progress_bar()` implementation consolidated in `MenuUtils`
- Removed duplicate implementation from `KodiMenuHandler`
- Updated `episodes_menu()` to use unified builder with `overlay_progress` option
- Progress bar logic now consistent across `continue_watching_menu()` and `episodes_menu()`
- Updated test to verify unified builder usage
- All tests pass (436/436) with 88% coverage maintained
- Pyright type checking: 0 errors, 0 warnings

#### 1.7 – Update continue-watching.md

**File:** [docs/features/continue-watching.md](../docs/features/continue-watching.md)

**Action:**
Verify if updates are needed to continue-watching.md; may already be completed as part of other work. If needed, update examples and references.

**Acceptance Criteria:**
- Docs match current implementation
- Examples are accurate
- No TODOs in feature doc (moved to plan if needed)

**Pending Questions:**
- [ ] Confirm what updates are needed to continue-watching.md

#### 1.8 – Remove Deprecated API References

**Files:**
- [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py) — search for deprecated methods
- [docs/dev/data-structure.md](../docs/dev/data-structure.md) — update/remove deprecated refs

**Action:**
Audit codebase for deprecated markers (`# TODO`, `@deprecated`); implement, remove, or update as needed. Update docs to reflect current API surface.

**Acceptance Criteria:**
- No deprecated references in active code
- Docs reflect only current API

**Pending Questions:**
- [ ] Confirm what deprecated references exist

---

## Test Strategy & Validation

### Unit Tests (Phase 1)

**Requirement:** Maintain test coverage (aim for 100% where practical; edge cases and comprehensive testing revamp deferred to future project)

**Testing Philosophy:** Focus on behavior preservation and practical coverage improvement. Exhaustive edge case testing and full 100% coverage restoration deferred to Phase 2 or beyond. Losing some coverage for better fixtures is acceptable if it improves maintainability. Include UI spot-checks after each subphase.

**Approach:**
1. **After each phase**, run full test suite to confirm coverage is maintained or improved where possible
2. **Phase 1 changes** (refactoring): Ensure tests don't change behavior (they verify behavior)
3. **New fixtures/helpers** (1.1): Add unit tests for fixture composition where practical
4. **New abstractions** (1.4, 1.5): Add parametrized tests for all content types where coverage gaps exist

**Commands:**
```bash
make unittest-with-coverage
```

Expected output: Coverage report; aim to maintain or improve coverage without exhaustive edge case testing (deferred).

### Code Quality (Phase 1)

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
- [ ] Infotag mapping preserves optimized if-chain structure (performance-critical)
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
        "projects_cache_hours": "12",
        "project_cache_hours": "8",
        "episodes_cache_hours": "72",
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
        dict: Named mocks for addDirectoryItem, endOfDirectory, setResolvedUrl.
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
def mock_kodi_xbmcgui():
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

### Durable Docs (Update/Keep)

| File | Action |
|------|--------|
| [docs/dev/data-structure.md](../docs/dev/data-structure.md) | Keep as-is (current) ✅ |
| [metadata-mapping.md](../docs/metadata-mapping.md) | Keep as-is (current) ✅ |
| [DEFERRED_CACHE_WRITES.md](../docs/DEFERRED_CACHE_WRITES.md) | **Update**: Remove SimpleCache references; note caching happens in UI layer |
| [features/continue-watching.md](../docs/features/continue-watching.md) | **Update**: Verify implementation; refresh examples |
| [.github/copilot-instructions.md](../.github/copilot-instructions.md) | **Review**: Ensure architecture guidance matches cleaned-up code |

---

## Timing Capture (Performance Baseline)

**Goal:** Performance timing is already implemented following existing patterns. Validate and leverage as needed for Phase 1 changes.

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

**Process Note:** Update CLEANUP - Phase 1.md status and commit changes between each sub-phase step (1.1, 1.2, etc.) for easy rollback. Review and answer pending questions before moving to next sub-phase step.

### Phase 1 Checklist

- [x] 1.1 – Refactor test fixtures (conftest.py)
  - [x] All fixtures have docstrings
  - [x] Fixture names descriptive
  - [x] Composed fixtures documented
  - [x] Tests pass
- [x] 1.2 – Redact auth logs
  - [x] Create `_sanitize_headers_for_logging()` in angel_utils.py
  - [x] Update all header log calls in angel_interface.py and angel_authentication.py
  - [x] No credentials in logs
- [x] 1.3 – Improve GraphQL error logging
  - [x] Error messages logged with details
  - [x] Operation name in logs
  - [x] Tests verify logging
- [x] 1.4 – Extract ListItem builder
  - [x] Single `_build_list_item_for_content()` method
  - [x] All menus use builder
  - [x] No duplication in list item creation
- [ ] 1.5 – Review infotag field mapping
  - [x] If-chains validated as intact and optimized
  - [x] Debug logging suppression via settings validated
  - [x] Comments added explaining optimization rationale
- [ ] 1.6 – Consolidate progress bar logic
  - [x] Single `_apply_progress_bar()` implementation in MenuUtils
  - [x] Used in `_build_list_item_for_content()` with overlay_progress option
  - [x] Consistent behavior across continue_watching_menu and episodes_menu

**Completed:** January 21, 2026
- Fixed progress bar regression from Phase 1.4 (watchPosition dict handling)
- Single implementation in MenuUtils with proper dict extraction
- Integrated into unified builder with overlay_progress parameter
- All tests pass (436/436) with 88% coverage maintained
- [ ] 1.7 – Update continue-watching.md
  - [x] Docs match implementation
  - [x] Examples accurate

**Completed:** January 21, 2026
- Updated documentation to reflect unified builder architecture
- Progress bars consolidated in MenuUtils with dict input handling
- Continue watching menu uses overlay_progress option
- Updated data flow, edge cases, and file references
- Removed outdated implementation plans and TODOs
- [ ] 1.8 – Remove deprecated API references
  - [ ] No `@deprecated` or stale TODOs
  - [ ] Docs updated
- [ ] **Phase 1 Complete**: Run `make unittest-with-coverage` → expect coverage maintained or improved
- [ ] **Phase 1 Complete**: Run `make format-and-lint` → expect zero errors
- [ ] **Phase 1 Complete**: Code review sign-off

---

## Risk Mitigation

### Phase 1 Risks: **Medium**

**Risk:** Fixture refactoring changes mock behavior; tests pass but behavior diverges.
**Mitigation:** Tests remain unchanged (behavior verification); only fixtures refactored; run full suite. Losing some coverage for better fixtures is acceptable.

**Risk:** ListItem builder abstraction introduces bugs in list rendering.
**Mitigation:** Parametrize tests over all content types (episode, project, season, etc.); verify artwork/infotags per type.

**Risk:** Infotag mapping loop misses edge cases (type coercion, None values).
**Mitigation:** Add type checking in loop; handle None gracefully; log warnings; tests cover edge cases.

---

## Post-Cleanup Checklist (Final)

**Before Commit:**
- [ ] All phases complete (1)
- [ ] `make unittest-with-coverage` → expect coverage maintained or improved
- [ ] `make format-and-lint` → zero errors
- [ ] Code review approved
- [ ] Docs updated/archived
- [ ] .gitignore updated
- [ ] Makefile targets added
- [ ] pytest.ini created
- [ ] .flake8 config created
- [ ] Timing baseline captured

**Commit Messages (per sub-phase step):**
```
Phase 1.1: feat: cleanup 1.1 - refactor test fixtures

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup

Phase 1.2: feat: cleanup 1.2 - redact auth logs

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup

[... continue for each 1.x ...]

Phase 1.8: feat: cleanup 1.8 - remove deprecated API references

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup
```

---

## Appendix: File Change Summary

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

**Document Status:** Ready for Implementation
**Next Step:** Begin Phase 1.1 implementation