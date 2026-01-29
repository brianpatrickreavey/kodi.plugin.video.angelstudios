# Authentication Module Refactor Plan

## Status: In Progress
**Last Updated:** 2026-01-28
**Agent:** GitHub Copilot (Claude Sonnet 4.5)

---

## Executive Summary

Refactor the authentication module to address critical architectural flaws introduced by a previous developer. The current implementation has created a tangled web of dependencies between `angel_authentication.py`, `angel_interface.py`, and `kodi_ui_interface.py` that violates separation of concerns, creates circular dependencies, and makes the code fragile and difficult to test.

### Critical Issues
1. **Circular dependency hell**: Authentication imports UI, UI imports Angel Interface, Angel Interface imports Authentication
2. **UI entanglement**: Authentication module directly calls Kodi UI functions for dialogs
3. **Session management chaos**: Multiple classes trying to manage session state
4. **Poor testability**: Tight coupling makes unit testing nearly impossible
5. **Fragile error handling**: Authentication errors bubble up through multiple layers

---

## Goals & Non-Goals

### Primary Goals
- ✅ Eliminate circular dependencies between authentication, API, and UI layers
- ✅ Create clean separation of concerns with proper abstraction boundaries
- ✅ Make authentication logic independently testable
- ✅ Implement proper error handling with clear failure modes
- ✅ Maintain or improve UX (no regressions in user experience)

### Non-Goals
- ❌ Changing the authentication protocol/API contract with Angel Studios
- ❌ Modifying the UI presentation layer (dialogs, input forms)
- ❌ Altering caching behavior for project/episode data
- ❌ Touching unrelated modules (video playback, GraphQL queries, etc.)

---

## Research Phase Findings

### Current Architecture Analysis

#### Module Dependencies (Current - BROKEN)
```
kodi_ui_interface.py
    ↓ imports
angel_interface.py
    ↓ imports
angel_authentication.py
    ↓ imports (CIRCULAR!)
kodi_ui_interface.py
```

#### Key Components
1. **`AngelStudioSession`** (angel_authentication.py)
   - Manages OAuth-like authentication flow
   - Stores session tokens
   - PROBLEM: Directly calls `show_error()` from UI layer

2. **`AngelInterface`** (angel_interface.py)
   - GraphQL API client
   - Uses `AngelStudioSession` for auth
   - PROBLEM: Mixes API logic with authentication logic

3. **`KodiUIInterface`** (kodi_ui_interface.py)
   - UI presentation layer
   - PROBLEM: Creates session objects, handles auth state

### Test Coverage Analysis
- Current: `angel_authentication.py` has ~85% coverage but tests are brittle
- Tests mock UI layer, creating false confidence
- Integration points not properly tested

---

## Proposed Architecture

### New Module Structure

```
┌─────────────────────────────────────────┐
│     kodi_ui_interface.py (UI Layer)     │
│  - User interaction                     │
│  - Dialog presentation                  │
│  - No business logic                    │
└──────────────┬──────────────────────────┘
               │ uses (via dependency injection)
               ↓
┌─────────────────────────────────────────┐
│  angel_interface.py (API Client Layer)  │
│  - GraphQL operations                   │
│  - Data transformation                  │
│  - Cache management                     │
└──────────────┬──────────────────────────┘
               │ uses
               ↓
┌─────────────────────────────────────────┐
│ angel_authentication.py (Auth Core)     │
│  - Token management                     │
│  - Session validation                   │
│  - Auth flow orchestration              │
│  - NO UI DEPENDENCIES                   │
└─────────────────────────────────────────┘
```

### Key Design Principles

1. **Dependency Inversion**: Auth core depends on abstractions (callbacks), not concrete UI
2. **Single Responsibility**: Each module has ONE clear purpose
3. **Interface Segregation**: Minimal, focused interfaces between layers
4. **Tell, Don't Ask**: Components emit events/errors; callers decide how to handle

### New Component Definitions

#### `AuthenticationCore` (angel_authentication.py)
```python
class AuthenticationCore:
    """Pure authentication logic - no UI dependencies"""

    def __init__(self,
                 session_store: SessionStore,
                 error_callback: Callable[[str, str], None] = None):
        """
        session_store: Abstraction for persisting tokens
        error_callback: Optional callback for auth errors
        """

    def authenticate(self, username: str, password: str) -> AuthResult
    def validate_session(self) -> bool
    def refresh_token(self) -> bool
    def logout(self) -> None
```

#### `SessionStore` (new abstraction in angel_authentication.py)
```python
class SessionStore(ABC):
    """Abstract session persistence"""
    @abstractmethod
    def save_token(self, token: str) -> None

    @abstractmethod
    def get_token(self) -> Optional[str]

    @abstractmethod
    def clear_token(self) -> None

class KodiSessionStore(SessionStore):
    """Kodi addon settings implementation"""
    # Uses xbmcaddon.Addon().setSetting()
    # JWT token stored in invisible setting (level 4 - Internal)
    # Setting definition in resources/settings.xml:
    # <setting id="jwt_token" type="string" label="JWT Token" help="Internal JWT token storage">
    #     <level>4</level>  <!-- Internal - never shown in GUI -->
    #     <default/>
    #     <constraints><allowempty>true</allowempty></constraints>
    #     <!-- No <control> element - completely invisible -->
    # </setting>
    # User-facing controls provided via action buttons (clear_token, show_token_info)
```

#### `AngelInterface` (angel_interface.py - refactored)
```python
class AngelInterface:
    """GraphQL API client with authentication awareness"""

    def __init__(self, auth_core: AuthenticationCore):
        self.auth = auth_core

    def get_project(self, slug: str) -> dict:
        """Fetch project, handling auth transparently"""
        if not self.auth.validate_session():
            raise AuthenticationRequiredError()
        # ... GraphQL logic
```

#### `KodiUIInterface` (kodi_ui_interface.py - refactored)
```python
class KodiUIInterface:
    """UI orchestration - owns the user experience"""

    def __init__(self):
        session_store = KodiSessionStore(self.addon)
        self.auth = AuthenticationCore(
            session_store=session_store,
            error_callback=self._handle_auth_error
        )
        self.api = AngelInterface(self.auth)

    def _handle_auth_error(self, error_type: str, message: str):
        """Translate auth errors into UI actions"""
        self.show_error(f"Authentication Error: {message}")

    def ensure_authenticated(self) -> bool:
        """Interactive authentication flow"""
        if self.auth.validate_session():
            return True
        return self._prompt_for_login()
```

---

## Implementation Plan

### Phase 1: Foundation & Abstraction (3-4 hours)
**Goal**: Create new abstractions without breaking existing code

#### Step 1.1: Create SessionStore Abstraction
- [ ] Define `SessionStore` ABC in `angel_authentication.py`
- [ ] Implement `KodiSessionStore` (uses xbmcaddon settings)
- [ ] Write unit tests for `KodiSessionStore`
- **Validation**: Tests pass, no existing code broken

#### Step 1.2: Refactor AuthenticationCore
- [ ] Extract pure auth logic from `AngelStudioSession`
- [ ] Remove all `xbmcgui` imports from auth module
- [ ] Add error_callback parameter (optional, defaults to None)
- [ ] Update auth methods to return `AuthResult` dataclass
- **Validation**: Auth tests pass without UI mocks

#### Step 1.3: Update Tests
- [ ] Refactor `test_angel_authentication.py` to use new abstractions
- [ ] Add integration tests for SessionStore
- [ ] Verify 100% coverage maintained
- **Validation**: `make unittest-with-coverage` passes

---

### Phase 2: Break Circular Dependencies (2-3 hours)
**Goal**: Eliminate import cycles by inverting control flow

#### Step 2.1: Refactor AngelInterface
- [ ] Remove direct auth UI calls from `angel_interface.py`
- [ ] Accept `AuthenticationCore` via dependency injection
- [ ] Raise `AuthenticationRequiredError` instead of calling UI
- [ ] Update GraphQL methods to use auth validation
- **Validation**: API tests pass, no UI imports in angel_interface

#### Step 2.2: Update Error Handling
- [ ] Define custom exception hierarchy:
  - `AuthenticationRequiredError`
  - `SessionExpiredError`
  - `InvalidCredentialsError`
- [ ] Remove error dialogs from auth/API layers
- **Validation**: Exceptions properly defined and documented

#### Step 2.3: Update Tests
- [ ] Refactor `test_angel_interface.py` for new error handling
- [ ] Add tests for exception propagation
- **Validation**: Coverage remains 100%

---

### Phase 3: Refactor UI Layer (3-4 hours)
**Goal**: Make UI the orchestrator, handling auth UX

#### Step 3.1: Update KodiUIInterface Initialization
- [ ] Create `SessionStore` in UI __init__
- [ ] Instantiate `AuthenticationCore` with store + callback
- [ ] Pass auth core to `AngelInterface`
- [ ] Add `_handle_auth_error()` callback method
- **Validation**: Plugin initializes without errors

#### Step 3.2: Implement Interactive Auth Flow
- [ ] Create `ensure_authenticated()` method
- [ ] Add `_prompt_for_login()` with user input dialogs
- [ ] Update menu handlers to check auth before API calls
- [ ] Handle auth errors at UI boundary
- **Validation**: Manual testing of login flow

#### Step 3.3: Remove Old Dependencies
- [ ] Delete obsolete auth methods from UI
- [ ] Clean up imports across all modules
- [ ] Remove dead code paths
- **Validation**: Static analysis (pyright) clean

#### Step 3.4: Update Tests
- [ ] Refactor `test_kodi_ui_interface.py` for new flow
- [ ] Add integration tests for auth + API + UI
- [ ] Test error scenarios (bad credentials, expired session)
- **Validation**: All tests pass, 100% coverage

---

### Phase 4: Integration & Validation (2-3 hours)
**Goal**: Ensure everything works end-to-end

#### Step 4.1: Integration Testing
- [ ] Test full login flow (fresh install)
- [ ] Test session persistence (restart addon)
- [ ] Test session expiry handling
- [ ] Test invalid credentials
- [ ] Test network errors during auth
- **Validation**: All scenarios handled gracefully

#### Step 4.2: Performance Testing
- [ ] Verify no performance regressions
- [ ] Check cache behavior unchanged
- [ ] Validate API call counts (no extra requests)
- **Validation**: Performance metrics documented

#### Step 4.3: Final Validation
- [ ] Run full test suite: `make unittest-with-coverage`
- [ ] Verify 100% coverage maintained
- [ ] Run static analysis: `pyright`
- [ ] Manual UX testing in Kodi
- **Validation**: All checks pass

---

### Phase 5: Documentation & Cleanup (1-2 hours)

#### Step 5.1: Code Documentation
- [ ] Update docstrings for all modified methods
- [ ] Add module-level documentation
- [ ] Document new abstractions (SessionStore, AuthResult)
- [ ] Add usage examples in docstrings

#### Step 5.2: Update Project Documentation
- [ ] Update `docs/dev/architecture.md` with new auth flow
- [ ] Document error handling patterns
- [ ] Update testing guidelines
- [ ] Add migration notes for future developers

#### Step 5.3: Final Cleanup
- [ ] Remove any debug logging added during refactor
- [ ] Ensure code style consistency
- [ ] Update CHANGELOG.md
- [ ] Final commit with comprehensive commit message

---

## Risk Assessment & Mitigation

### High-Risk Areas

1. **Session Migration**
   - Risk: Existing users' sessions may be invalidated
   - Mitigation: Maintain backward compatibility in SessionStore

2. **Error Handling Changes**
   - Risk: Unhandled exceptions causing crashes
   - Mitigation: Comprehensive exception testing, graceful fallbacks

3. **UI/UX Regression**
   - Risk: Login flow becomes confusing or broken
   - Mitigation: Extensive manual testing, preserve existing dialogs

### Testing Strategy

- **Unit Tests**: Each component tested in isolation
- **Integration Tests**: Full auth flow tested end-to-end
- **Manual Testing**: Real Kodi environment validation
- **Regression Testing**: Verify existing features still work

---

## Success Criteria

### Technical Metrics
- ✅ Zero circular dependencies (verified by import analysis)
- ✅ 100% test coverage maintained
- ✅ All pyright checks pass (no type errors)
- ✅ No UI imports in auth or API layers
- ✅ All existing tests pass (no regressions)

### Functional Metrics
- ✅ Login flow works identically to before
- ✅ Session persistence works across addon restarts
- ✅ Error messages are clear and actionable
- ✅ No increase in API call count
- ✅ Performance identical or better

---

## Open Questions & Decisions Needed

### Architecture Decisions
1. **Callback vs Event Pattern**: Use simple callbacks or more robust event system?
   - **Recommendation**: Start with callbacks, can evolve to events if needed

2. **AuthResult Structure**: What should this dataclass contain?
   - **Recommendation**: `success: bool`, `token: Optional[str]`, `error_message: Optional[str]`

3. **Session Validation Frequency**: When should we validate tokens?
   - **Recommendation**: On startup + before each API call (with caching)

### Testing Decisions
1. **Integration Test Scope**: How much to test in integration vs unit tests?
   - **Recommendation**: Focus on unit tests, minimal integration for happy path

2. **Mock Strategy**: How to mock Kodi APIs in auth tests?
   - **Recommendation**: Use SessionStore abstraction, no Kodi mocks in auth tests

### UX Decisions
1. **Re-authentication Flow**: When session expires, auto-prompt or show error first?
   - **Recommendation**: Auto-prompt with clear message about session expiry

2. **Login Persistence**: How long should sessions last?
   - **Recommendation**: Keep existing behavior (token expiry from API)

---

## Implementation Notes

### Coding Standards
- Follow existing project conventions (see copilot-instructions.md)
- Use type hints for all public methods
- Maintain 100% test coverage (no `# pragma: no cover` without approval)
- Use parenthesized `with` blocks for multiple context managers
- Verbose, readable code over clever implementations

### Testing Requirements
- Every new method must have unit tests
- Every error path must be tested
- Use `@pytest.mark.parametrize` for multiple scenarios
- Mock external dependencies (network, Kodi APIs)
- Tests must be deterministic and fast

### Documentation Requirements
- All public methods require docstrings
- Complex logic needs inline comments
- Update module-level docs
- Add examples for non-obvious usage

---

## Rollback Plan

If major issues discovered during implementation:

1. **Immediate**: Revert commits to last stable state
2. **Investigation**: Analyze what went wrong, update plan
3. **Decision Point**: Fix forward or redesign approach
4. **Communication**: Document lessons learned

---

## Next Steps

### Ready to Proceed?
Before starting implementation, confirm:
- [ ] Architecture approach approved
- [ ] Success criteria agreed upon
- [ ] Risk mitigation acceptable
- [ ] Open questions resolved

### Phase 1 Kickoff
Once approved, begin with:
1. Create SessionStore abstraction
2. Write tests for SessionStore
3. Implement KodiSessionStore
4. Validate with `make unittest-with-coverage`

---

## Progress Tracking

### Phase 1: Foundation & Abstraction
- [ ] Step 1.1: Create SessionStore Abstraction
- [ ] Step 1.2: Refactor AuthenticationCore
- [ ] Step 1.3: Update Tests

### Phase 2: Break Circular Dependencies
- [ ] Step 2.1: Refactor AngelInterface
- [ ] Step 2.2: Update Error Handling
- [ ] Step 2.3: Update Tests

### Phase 3: Refactor UI Layer
- [ ] Step 3.1: Update KodiUIInterface Initialization
- [ ] Step 3.2: Implement Interactive Auth Flow
- [ ] Step 3.3: Remove Old Dependencies
- [ ] Step 3.4: Update Tests

### Phase 4: Integration & Validation
- [ ] Step 4.1: Integration Testing
- [ ] Step 4.2: Performance Testing
- [ ] Step 4.3: Final Validation

### Phase 5: Documentation & Cleanup
- [ ] Step 5.1: Code Documentation
- [ ] Step 5.2: Update Project Documentation
- [ ] Step 5.3: Final Cleanup

---

## Notes & Observations

*This section will be updated as work progresses with key insights, challenges, and decisions made during implementation.*

---

## References

- Project Architecture: `docs/dev/architecture.md`
- Testing Standards: See copilot-instructions.md
- API Documentation: `docs/features/angel-api.md`
- Current Implementation:
  - `plugin.video.angelstudios/resources/lib/angel_authentication.py`
  - `plugin.video.angelstudios/resources/lib/angel_interface.py`
  - `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
