# Project Cleanup Plan - Phase 2

**Date:** January 20, 2026
**Status:** Phase 2 deferred
**Owner:** Architecture & Product
**Audience:** Developer, Code Reviewer, QA

---

## Executive Summary

This cleanup plan addresses code organization, import strategy, caching patterns, authentication, UI consistency, error handling, logging, tests, and documentation accumulated during multi-feature development. The goal is to establish a clean, maintainable baseline before committing these features.

**Scope:**
- **Out of Scope (defer to next feature):** Session refresh token strategy, resumeWatching caching, integration tests, major architectural shifts.

**Risk Profile:**
- **Phase 2:** Medium-to-high risk (behavioral changes; deferred post-commit).

**Timeline Estimate:**
- Phase 2: 8+ hours (deferred)

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
- resumeWatching results not cached (deferred to Phase 2)

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

### Phase 2: Deeper Improvements *(Higher Risk — Deferred to Next Feature)*

This phase introduces behavioral changes and is **deferred post-commit**. Documented here for future reference.

#### 2.1 – Implement Session Refresh Token Strategy

**Status:** DEFERRED

**Scope:** [plugin.video.angelstudios/resources/lib/angel_authentication.py](../plugin.video.angelstudios/resources/lib/angel_authentication.py)

**Current:** Session validated on-demand; full re-auth if invalid.
**Proposed:** Refresh token logic; proactive refresh before expiry.

**Action:**
1. Add refresh token storage to session persistence
2. Implement `_refresh_session()` method that uses refresh token
3. Modify `_validate_session()` to attempt refresh before full re-auth
4. Add refresh token expiry handling

**Example Implementation:**
```python
def _refresh_session(self):
    """Attempt to refresh the session using stored refresh token."""
    if not self._refresh_token or not self._refresh_token_expiry:
        return False

    if datetime.now() > self._refresh_token_expiry:
        # Refresh token expired, need full re-auth
        return False

    # Make refresh request
    refresh_data = {
        "refreshToken": self._refresh_token,
        "grant_type": "refresh_token"
    }

    try:
        response = self.session.post(
            f"{self.base_url}/oauth/token",
            json=refresh_data,
            timeout=30
        )
        response.raise_for_status()
        token_data = response.json()

        # Update session with new tokens
        self.session.headers.update({
            "Authorization": f"Bearer {token_data['access_token']}"
        })
        self._access_token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'])
        self._refresh_token = token_data.get('refresh_token', self._refresh_token)
        self._refresh_token_expiry = datetime.now() + timedelta(days=30)  # Assume 30-day refresh expiry

        # Persist updated session
        self._persist_session()
        return True

    except Exception as e:
        self.log.debug(f"Session refresh failed: {e}")
        return False

def _validate_session(self):
    """Validate session, attempting refresh if needed."""
    if not self.session or not self._access_token_expiry:
        return False

    # Check if access token is still valid with buffer
    if datetime.now() < (self._access_token_expiry - timedelta(minutes=5)):
        return True

    # Try to refresh
    if self._refresh_session():
        return True

    # Refresh failed, need full re-auth
    return False
```

**Acceptance Criteria:**
- Session refresh attempted before full re-auth
- Refresh tokens stored securely (encrypted if possible)
- Token expiry handled gracefully
- Tests cover refresh success/failure scenarios
- No breaking changes to existing auth flow

**Pending Questions:**
- [ ] Confirm refresh token API endpoints and format
- [ ] Determine refresh token storage security requirements

#### 2.2 – Add Integration Tests

**Status:** DEFERRED

**Scope:** `tests/integration/` (new)

**Proposed:** Tests that exercise full flow (API + UI + caching).

**Action:**
1. Create `tests/integration/` directory
2. Add integration test for complete user flows:
   - Project browsing → Episode selection → Playback
   - Continue watching → Resume playback
   - Cache hit/miss scenarios
3. Use real HTTP calls with test credentials (separate from unit tests)
4. Mock only external dependencies (Kodi UI, file system)

**Example Test Structure:**
```python
# tests/integration/test_project_browse_flow.py
def test_project_browse_to_episode_playback():
    """Test complete flow from project list to episode playback."""
    # Setup: Authenticate with test account
    # Action: Browse projects → Select project → Browse episodes → Select episode
    # Assert: Playback URL generated correctly, metadata populated

# tests/integration/test_continue_watching_flow.py
def test_continue_watching_resume():
    """Test continue watching with resume functionality."""
    # Setup: Mock partial watch progress
    # Action: Load continue watching menu → Select item → Resume playback
    # Assert: Resume time applied correctly
```

**Acceptance Criteria:**
- Integration tests run separately from unit tests
- Test credentials isolated from production
- Full user flows validated
- CI/CD integration for integration test suite

**Pending Questions:**
- [ ] Confirm test account setup and credentials management
- [ ] Determine integration test frequency (nightly vs on-demand)

#### 2.4 – Optimize KodiLogger Performance

**Status:** DEFERRED

**Scope:** [plugin.video.angelstudios/resources/lib/kodi_utils.py](../plugin.video.angelstudios/resources/lib/kodi_utils.py) (KodiLogger)

**Current:** Stack introspection on every log call (9 frames checked).
**Proposed:** Cache frame info or use faster caller detection.

**Action:**
1. Analyze current stack inspection usage
2. Implement caching for frame information
3. Consider alternative caller detection methods

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
- Logging performance improved (measure with timing tests)
- Caller info still accurate for debugging
- Memory usage reasonable (cache doesn't grow unbounded)
- Backward compatibility maintained

**Pending Questions:**
- [ ] Measure current performance impact
- [ ] Confirm acceptable trade-offs for accuracy vs performance

---

## Test Strategy & Validation

### Integration Tests (Phase 2)

**Requirement:** Add integration tests for full user flows.

**Testing Philosophy:** Validate end-to-end functionality with real API calls and minimal mocking.

**Approach:**
1. **Separate test suite**: `tests/integration/` runs independently
2. **Test credentials**: Use dedicated test account/API keys
3. **Mock boundaries**: Only mock Kodi UI and file system; use real HTTP
4. **CI/CD**: Run integration tests nightly or on-demand

**Commands:**
```bash
make integration-tests
```

Expected output: Integration test results; focus on flow validation over edge cases.

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
- [ ] Session refresh implemented without breaking existing auth
- [ ] Integration tests validate full flows
- [ ] KodiLogger performance optimized
- [ ] All user-visible behavior preserved

---

## Configuration Updates

### Update Makefile

**File:** [Makefile](../Makefile)

**Add targets:**
```makefile
.PHONY: integration-tests
integration-tests:
	pytest tests/integration/ -v --tb=short

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

# Integration test credentials
test_credentials_integration.json
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

**Process Note:** Phase 2 deferred to next feature cycle. Documented here for future reference.

### Phase 2 Checklist

- [ ] 2.1 – Implement Session Refresh Token Strategy
  - [ ] Refresh token storage implemented
  - [ ] `_refresh_session()` method added
  - [ ] `_validate_session()` updated to use refresh
  - [ ] Tests cover refresh scenarios
- [ ] 2.2 – Add Integration Tests
  - [ ] `tests/integration/` directory created
  - [ ] Full flow tests implemented
  - [ ] Test credentials configured
  - [ ] CI/CD integration added
- [ ] 2.4 – Optimize KodiLogger Performance
  - [ ] Stack inspection optimized
  - [ ] Performance measured and improved
  - [ ] Accuracy maintained
- [ ] **Phase 2 Complete**: Run `make integration-tests` → validate full flows
- [ ] **Phase 2 Complete**: Run `make performance-test` → measure improvements
- [ ] **Phase 2 Complete**: Code review sign-off

---

## Risk Mitigation

### Phase 2 Risks: **Higher** (deferred)

Session refresh / resumeWatching caching could affect auth flow or cache invalidation. Deferred to next feature for dedicated testing.

**Risk:** Session refresh introduces auth failures.
**Mitigation:** Fallback to full re-auth; extensive testing of refresh scenarios.

**Risk:** Integration tests flaky due to external dependencies.
**Mitigation:** Use dedicated test environment; retry logic; separate from unit tests.

**Risk:** Logger optimization breaks debugging.
**Mitigation:** Maintain caller info accuracy; performance gains validated.

---

## Post-Cleanup Checklist (Final)

**Before Commit:**
- [ ] All phases complete (2)
- [ ] `make unittest-with-coverage` → expect coverage maintained or improved
- [ ] `make integration-tests` → validate full flows
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
Phase 2.1: feat: implement session refresh token strategy

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup

Phase 2.2: feat: add integration tests

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup

[... continue for each 2.x ...]

Phase 2.4: feat: optimize KodiLogger performance

Completed: [list specific files/changes]
- Test coverage maintained or improved

Refs: #cleanup
```

---

## Appendix: File Change Summary

### Phase 2 Changes

| File | Change Type | Scope |
|------|---|---|
| `resources/lib/angel_authentication.py` | Add refresh token logic | ~50 lines |
| `tests/integration/` | New directory with tests | ~200 lines |
| `resources/lib/kodi_utils.py` | Optimize KodiLogger | ~30 lines |
| `Makefile` | Add integration targets | ~10 lines |
| `pytest.ini` | Update for integration | ~5 lines |
| `.gitignore` | Add integration artifacts | ~5 lines |

---

**Document Status:** Deferred for future implementation
**Next Step:** Complete Phase 1, then revisit Phase 2 in next feature cycle