# Project Cleanup Plan - Phase 2

**Date:** January 21, 2026
**Status:** In Progress (Phases 2.2 & 2.3 Complete)
**Owner:** Architecture & Product
**Audience:** Developer, Code Reviewer, QA

---

## Executive Summary

This cleanup plan addresses code organization, import strategy, caching patterns, authentication, UI consistency, error handling, logging, tests, and documentation accumulated during multi-feature development. The goal is to establish a clean, maintainable baseline before committing these features.

**Scope:**
- **Out of Scope:** Major architectural shifts, session refresh tokens (moved to separate feature).

**Risk Profile:**
- **Phase 2:** Medium risk (behavioral changes; implement with caution).

**Timeline Estimate:**
- Phase 2: 8+ hours

**Success Criteria:**
1. All phases complete with test coverage maintained (aim for 100% where practical; edge cases deferred to future testing revamp)
2. All code passes black + flake8 formatting.
3. Fixture refactoring improves readability (verified via code review).
4. No user-visible behavior changes (seamless UX preserved).
5. All docs updated/archived.

---

## Current State Assessment (Post Phase 1)

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

### Known Issues (from Audit, Post Phase 1)

**Imports:**
- ✅ Unused imports removed (Phase 0)
- ✅ Duplicate imports removed (Phase 0)
- Optional addon detection uses correct pattern ✅

**Caching:**
- ✅ Separate cache TTL settings added (Phase 0)
- Query/fragment in-memory file caches have no eviction strategy (but small, low-impact); consider renaming to clarify they cache file contents, not data responses (e.g., `_query_file_cache`, `_fragment_file_cache`)
- resumeWatching results not cached

**Auth:**
- No session refresh token logic; validation only on-demand
- ✅ Auth logs redacted (Phase 1)
- No request timeouts

**UI:**
- ✅ Long functions refactored with ListItem builder (Phase 1)
- ✅ Repetitive list item creation abstracted (Phase 1)
- ✅ Infotag field mapping reviewed (Phase 1)
- ✅ Progress bar logic consolidated (Phase 1)

**Logging:**
- KodiLogger stack introspection (9 frames) on every log call (performance concern)
- ✅ GraphQL errors logged with details (Phase 1)

**Tests & Fixtures:**
- ✅ Fixtures refactored for clarity (Phase 1)
- Test data centralized but fixture chains could be clearer
- Multi-patch context managers correct ✅; documentation lacking

**Docs:**
- ✅ Research docs archived (Phase 0)
- ✅ continue-watching.md updated (Phase 1)
- ✅ Deprecated API references removed (Phase 1)

---

## Cleanup Phases

### Phase 2: Deeper Improvements

#### 2.1 – Add Request Timeouts

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py), [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)

**Current:** No request timeouts configured; requests may hang indefinitely.
**Proposed:** Add configurable timeouts to all HTTP requests.

**Action:**
1. Add timeout constants (30s for auth, 10s for API calls) - make configurable via settings (Expert/level3)
2. Update all `requests` calls to include `timeout` parameter
3. Handle timeout exceptions: log all errors, handle expected errors (bad credentials, etc.) with visual notifications, catch unexpected errors and log them - both should raise visual notifications
4. Consider HTTP-call helper for centralizing timeouts if beneficial
5. Verify all HTTP calls are in angel_authentication.py and angel_interface.py

**Example Implementation:**
```python
# In angel_authentication.py
TIMEOUT_AUTH = 30  # seconds

def _authenticate(self):
    # ... existing code ...
    response = self.session.post(
        f"{self.base_url}/oauth/token",
        json=auth_data,
        timeout=TIMEOUT_AUTH
    )

# In angel_interface.py
TIMEOUT_API = 10  # seconds

def _execute_graphql_query(self, query, variables=None):
    # ... existing code ...
    response = self.session.post(
        self.graphql_url,
        json=payload,
        timeout=TIMEOUT_API
    )
```

**Acceptance Criteria:**
- All HTTP requests have appropriate timeouts
- Timeouts configurable via Expert settings
- Timeout and other HTTP exceptions handled with proper logging and user notifications
- HTTP-call helper implemented if beneficial
- No unhandled HTTP calls found outside target files

#### 2.2 – Cache resumeWatching Results

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**Current:** resumeWatching results not cached; fetched on every menu load.
**Proposed:** Cache resumeWatching API responses to improve performance.

**Action:**
1. Identify resumeWatching API calls in UI methods
2. Add caching with configurable TTL (10 minutes default)
3. Cache paginated responses since API calls are paginated
4. Cache response from angel_interface, not HTTP call itself
5. Cache invalidation out of scope (revisit in feature-dedicated-player.md)

**Example Implementation:**
```python
def get_continue_watching_items(self):
    """Get continue watching items with caching."""
    cache_key = "continue_watching"
    cached_data = self.cache.get(cache_key)
    if cached_data:
        return cached_data

    # Fetch from API
    data = self.angel_interface.get_resume_watching()
    if data:
        self.cache.set(cache_key, data, ttl=600)  # 10 minutes
    return data
```

**Acceptance Criteria:**
- resumeWatching results cached with configurable 10-minute default TTL
- Paginated responses properly cached
- Performance improved for continue watching menu
- No stale data issues (invalidation handled in future feature)

#### 2.3 – Rename Query/Fragment Caches for Clarity + GraphQL DRY Refactoring

**Status:** READY

**Scope:** 
- [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)
- GraphQL files in [plugin.video.angelstudios/resources/lib/angel_graphql/](../plugin.video.angelstudios/resources/lib/angel_graphql/)

**Current:** 
- `_query_cache` and `_fragment_cache` cache file contents but names suggest data caching.
- Inline fragments in `query_resumeWatching.graphql` duplicate field definitions that exist in unused fragments.

**Proposed:** 
- Rename caches to `_query_file_cache` and `_fragment_file_cache` for clarity.
- Refactor `query_resumeWatching.graphql` to use named fragments instead of inline ones.
- Update existing fragments to match current field selections.
- Archive truly unused GraphQL files.

**Action:**
1. Rename cache attributes and references in `angel_interface.py`
2. Update `fragment_ContentMovie.graphql` and `fragment_ContentSpecial.graphql` to match inline fragment field selections
3. Replace inline `... on ContentMovie { ... }` and `... on ContentSpecial { ... }` in `query_resumeWatching.graphql` with `...ContentMovie` and `...ContentSpecial`
4. Archive unused files: `query_getEpisodeForPlayback.graphql`, `query_getProjectsForSlugs.graphql`, `fragment_ContentImage.graphql`
5. Update any related comments/documentation
6. Ensure no functional changes

**Example Implementation:**
```python
class AngelStudiosInterface:
    def __init__(self):
        self._query_file_cache = {}  # Cache for loaded query files
        self._fragment_file_cache = {}  # Cache for loaded fragment files
```

**Acceptance Criteria:**
- Cache names clearly indicate they cache file contents
- All references updated consistently
- GraphQL queries use named fragments instead of inline duplication
- Unused GraphQL files archived
- No external references broken
- No functional changes to caching or query behavior

#### 2.4 – Optimize KodiLogger Performance

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_utils.py](../plugin.video.angelstudios/resources/lib/kodi_utils.py) (KodiLogger)

**Current:** Stack introspection on every log call (9 frames checked).
**Proposed:** Cache frame info or use faster caller detection.

**Action:**
1. Analyze current stack inspection usage
2. Implement caching for frame information (ignore memory impact for now - not many frames)
3. Consider alternative caller detection methods
4. If no way to cache without sacrificing accuracy, abandon caching
5. Use existing PERF patterns for timing tests if implemented

**Example Optimization:**
```python
class KodiLogger:
    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)
        self._frame_cache = {}  # Cache for frame info

    def debug(self, message, *args, **kwargs):
        # Use cached or simplified caller info
        caller_info = self._get_caller_info()
        # ... format and log ...

    def _get_caller_info(self):
        """Get caller info with caching to reduce stack inspection."""
        frame = inspect.currentframe()
        try:
            # Walk up stack to find relevant caller
            for _ in range(3):  # Skip logger frames
                frame = frame.f_back
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            funcname = frame.f_code.co_name

            # Cache key based on filename/lineno
            cache_key = f"{filename}:{lineno}"
            if cache_key not in self._frame_cache:
                self._frame_cache[cache_key] = f"{filename}:{lineno} in {funcname}"

            return self._frame_cache[cache_key]
        finally:
            del frame
```

**Acceptance Criteria:**
- Logging performance improved (measure with timing tests if beneficial)
- Caller info still accurate for debugging
- If caching sacrifices accuracy, optimization abandoned
- Backward compatibility maintained

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py), [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)

**Current:** No request timeouts configured; requests may hang indefinitely.
**Proposed:** Add configurable timeouts to all HTTP requests.

**Action:**
1. Add timeout constants (30s for auth, 10s for API calls) - make configurable via settings (Expert/level3)
2. Update all `requests` calls to include `timeout` parameter
3. Handle timeout exceptions: log all errors, handle expected errors (bad credentials, etc.) with visual notifications, catch unexpected errors and log them - both should raise visual notifications
4. Consider HTTP-call helper for centralizing timeouts if beneficial
5. Verify all HTTP calls are in angel_authentication.py and angel_interface.py

**Example Implementation:**
```python
# In angel_authentication.py
TIMEOUT_AUTH = 30  # seconds

def _authenticate(self):
    # ... existing code ...
    response = self.session.post(
        f"{self.base_url}/oauth/token",
        json=auth_data,
        timeout=TIMEOUT_AUTH
    )

# In angel_interface.py
TIMEOUT_API = 10  # seconds

def _execute_graphql_query(self, query, variables=None):
    # ... existing code ...
    response = self.session.post(
        self.graphql_url,
        json=payload,
        timeout=TIMEOUT_API
    )
```

**Acceptance Criteria:**
- All HTTP requests have appropriate timeouts
- Timeouts configurable via Expert settings
- Timeout and other HTTP exceptions handled with proper logging and user notifications
- HTTP-call helper implemented if beneficial
- No unhandled HTTP calls found outside target files

#### 2.3 – Cache resumeWatching Results

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

**Current:** resumeWatching results not cached; fetched on every menu load.
**Proposed:** Cache resumeWatching API responses to improve performance.

**Action:**
1. Identify resumeWatching API calls in UI methods
2. Add caching with configurable TTL (10 minutes default)
3. Cache paginated responses since API calls are paginated
4. Cache response from angel_interface, not HTTP call itself
5. Cache invalidation out of scope (revisit in feature-dedicated-player.md)

**Example Implementation:**
```python
def get_continue_watching_items(self):
    """Get continue watching items with caching."""
    cache_key = "continue_watching"
    cached_data = self.cache.get(cache_key)
    if cached_data:
        return cached_data

    # Fetch from API
    data = self.angel_interface.get_resume_watching()
    if data:
        self.cache.set(cache_key, data, ttl=600)  # 10 minutes
    return data
```

**Acceptance Criteria:**
- resumeWatching results cached with configurable 10-minute default TTL
- Paginated responses properly cached
- Performance improved for continue watching menu
- No stale data issues (invalidation handled in future feature)

#### 2.4 – Rename Query/Fragment Caches for Clarity

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/angel_interface.py](../plugin.video.angelstudios/resources/lib/angel_interface.py)

**Current:** `_query_cache` and `_fragment_cache` cache file contents but names suggest data caching.
**Proposed:** Rename to `_query_file_cache` and `_fragment_file_cache` for clarity.

**Action:**
1. Rename cache attributes and references
2. Update any related comments/documentation
3. Assume no external references (investigate during implementation)
4. Consider archiving unused GraphQL files
5. Ensure no functional changes

**Example Implementation:**
```python
class AngelStudiosInterface:
    def __init__(self):
        self._query_file_cache = {}  # Cache for loaded query files
        self._fragment_file_cache = {}  # Cache for loaded fragment files
```

**Acceptance Criteria:**
- Cache names clearly indicate they cache file contents
- All references updated consistently
- No external references broken (investigate during implementation)
- Unused GraphQL files archived if found
- No functional changes to caching behavior

#### 2.5 – Optimize KodiLogger Performance

**Status:** READY

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_utils.py](../plugin.video.angelstudios/resources/lib/kodi_utils.py) (KodiLogger)

**Current:** Stack introspection on every log call (9 frames checked).
**Proposed:** Cache frame info or use faster caller detection.

**Action:**
1. Analyze current stack inspection usage
2. Implement caching for frame information (ignore memory impact for now - not many frames)
3. Consider alternative caller detection methods
4. If no way to cache without sacrificing accuracy, abandon caching
5. Use existing PERF patterns for timing tests if implemented

**Example Optimization:**
```python
class KodiLogger:
    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)
        self._frame_cache = {}  # Cache for frame info

    def debug(self, message, *args, **kwargs):
        # Use cached or simplified caller info
        caller_info = self._get_caller_info()
        # ... format and log ...

    def _get_caller_info(self):
        """Get caller info with caching to reduce stack inspection."""
        frame = inspect.currentframe()
        try:
            # Walk up stack to find relevant caller
            for _ in range(3):  # Skip logger frames
                frame = frame.f_back
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            funcname = frame.f_code.co_name

            # Cache key based on filename/lineno
            cache_key = f"{filename}:{lineno}"
            if cache_key not in self._frame_cache:
                self._frame_cache[cache_key] = f"{filename}:{lineno} in {funcname}"

            return self._frame_cache[cache_key]
        finally:
            del frame
```

**Acceptance Criteria:**
- Logging performance improved (measure with timing tests if beneficial)
- Caller info still accurate for debugging
- If caching sacrifices accuracy, optimization abandoned
- Backward compatibility maintained

---

## Test Strategy & Validation

### Code Quality (Phase 2)

**Commands:**
```bash
make lint      # pyright + flake8 + black check
black --line-length=120 plugin.video.angelstudios/ tests/
flake8 plugin.video.angelstudios/ tests/ --max-line-length=120
pyright
```

Expected: Zero errors; zero warnings; consistent formatting.

### Manual Verification

After Phase 2, **code review checklist:**
- [ ] Request timeouts added to all HTTP calls
- [ ] resumeWatching results cached appropriately
- [ ] Query/fragment caches renamed for clarity
- [ ] KodiLogger performance optimized
- [ ] All user-visible behavior preserved

---

## Configuration Updates

### Update Makefile

**File:** [Makefile](../Makefile)

**Add targets:**
```makefile
.PHONY: performance-test
performance-test:
	@echo "Running performance tests..."
	pytest tests/unit/ -k "timing" -v --tb=short
```

**Update existing targets** (if needed):
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
testpaths = tests/unit tests/integration
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
# Timing output for performance monitoring
markers =
    timing: marks tests related to timing instrumentation
    integration: marks integration tests (run separately)
```

---

## Progress Tracking

**Implementation Order:** Implement phases separately like Phase 1 (test, review, commit between steps).

### Phase 2 Checklist

- [x] 2.1 – Add Request Timeouts
  - [ ] Timeout constants defined (30s auth, 10s API)
  - [ ] All HTTP requests updated with timeouts
  - [ ] Configurable via Expert settings
  - [ ] Exception handling with logging and user notifications
  - [ ] HTTP-call helper implemented if beneficial
  - [ ] Verified all HTTP calls covered
- [x] 2.2 – Cache resumeWatching Results
  - [x] Caching added to resumeWatching methods with 5-minute TTL
  - [x] Debug promotion toggles added for granular logging control
  - [x] Paginated responses properly cached
  - [x] Confirmed working in KODI UI
- [x] 2.3 – Rename Query/Fragment Caches for Clarity + GraphQL DRY Refactoring
  - [x] Cache attributes renamed (_query_cache → _query_file_cache, _fragment_cache → _fragment_file_cache)
  - [x] GraphQL DRY refactoring: replaced inline fragments with named fragments in query_resumeWatching.graphql
  - [x] Updated fragment_ContentMovie.graphql and fragment_ContentSpecial.graphql to match current field selections
  - [x] Deleted unused GraphQL files (query_getEpisodeForPlayback.graphql, query_getProjectsForSlugs.graphql, fragment_ContentImage.graphql)
  - [x] All references updated consistently
  - [x] Tests updated and passing (445 tests, 88% coverage)
- [ ] 2.4 – Optimize KodiLogger Performance
  - [ ] Stack inspection optimized with caching
  - [ ] Accuracy maintained (abandon if not possible)
  - [ ] Performance measured if beneficial
- [ ] **Phase 2 Complete**: Run `make unittest-with-coverage` → coverage maintained
- [ ] **Phase 2 Complete**: Code review sign-off

---

## Risk Mitigation

### Phase 2 Risks: Medium

**Risk:** Request timeouts cause false failures.
**Mitigation:** Reasonable timeout values; proper exception handling with user notifications.

**Risk:** Caching resumeWatching leads to stale data.
**Mitigation:** Short configurable TTL; invalidation handled in future feature.

**Risk:** Logger optimization breaks debugging.
**Mitigation:** Maintain caller info accuracy; abandon caching if accuracy sacrificed.

**Risk:** Breaking changes affect users.
**Mitigation:** Pre-1.0 status allows breaking changes; thorough testing.

---

## Post-Cleanup Checklist (Final)

**Before Each Phase Commit:**
- [ ] Phase implemented and tested
- [ ] `make unittest-with-coverage` → coverage maintained or improved
- [ ] `make format-and-lint` → zero errors
- [ ] Code review approved
- [ ] Backward compatibility verified (pre-1.0 allows breaking changes)

**Commit Messages (per phase):**
```
Phase 2.1: feat: add request timeouts

Completed: [list specific files/changes]
- HTTP requests now have configurable timeouts
- Exception handling with user notifications added

Refs: #cleanup

[... continue for each 2.x ...]

Phase 2.4: feat: optimize KodiLogger performance

Completed: [list specific files/changes]
- Logging performance improved with frame caching

Refs: #cleanup
```

---

## Appendix: File Change Summary

### Phase 2 Changes

| File | Change Type | Scope |
|------|---|---|
| `resources/lib/angel_authentication.py` | Add timeouts | ~10 lines |
| `resources/lib/angel_interface.py` | Add timeouts + cache renaming | ~15 lines |
| `resources/lib/kodi_ui_interface.py` | Add resumeWatching caching | ~20 lines |
| `resources/lib/kodi_utils.py` | Optimize KodiLogger | ~30 lines |
| `Makefile` | Add performance targets | ~5 lines |
| `pytest.ini` | Update for integration | ~5 lines |
| `.gitignore` | Add artifacts | ~5 lines |

---

**Document Status:** Ready for implementation
**Next Step:** Implement Phase 2 changes