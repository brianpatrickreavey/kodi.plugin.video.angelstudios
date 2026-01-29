# Auth0 CIAM Package Extraction Plan

## Overview
This document tracks the extraction of `angel_authentication.py` into a reusable `auth0-ciam` Python package.

## Research Findings

### Existing Auth0 Packages Analysis
**auth0-login package (pypi.org/project/auth0-login/)**:
- CLI tool for obtaining JWT tokens via PKCE flow
- Designed for AWS integration, not general Auth0 CIAM
- No programmatic API - requires browser interaction
- No session persistence or token management
- Unmaintained (last release Feb 2021)
- **Conclusion**: Not suitable for our use case. Our implementation is more feature-complete for programmatic Auth0 CIAM usage in headless environments.

## Decision Tracking

### Package Naming
**Question 1**: What should be the package name on PyPI?
- Option A: `auth0-ciam` (generic, describes the Auth0 CIAM functionality)
- Option B: `auth0-ciam-client` (more specific about being a client)
- Option C: `angel-auth` (branded but less reusable)
- Option D: Other: __________
**Answer:** `auth0-ciam-client` - Explicitly indicates this is a client-side implementation for Auth0 CIAM, distinguishing it from server-side tools prevalent on PyPI.
**Rationale:** Given the abundance of server-side Auth0 tools on PyPI, being explicit about "client" helps users understand this is for client-side authentication flows, not server administration or API management.

### Licensing
**Question 2**: What license should the package use?
- Current Kodi addon uses GPL-3.0-only
- For maximum reusability, consider MIT or Apache 2.0
**Answer:** GPL-3.0-only (for now) - Maintains consistency with the current Kodi addon license. Can be adjusted to more permissive license before publishing if broader adoption is desired.
**Rationale:** Since this package is extracted from GPL-licensed Kodi addon code, starting with GPL-3.0 maintains license compatibility. The more permissive MIT/Apache licenses can be considered later if the package gains traction and broader adoption is prioritized over copyleft protection.

### Versioning
**Question 3**: Initial version number?
- Since this is extracted from working, tested code: `1.0.0`
- Or start at `0.1.0` for new package
**Answer:** `0.1.0` - Provides basic functionality sufficient for Angel Studios integration, but far from a complete Auth0 CIAM implementation.
**Rationale:** The extracted code works for Angel Studios but lacks many features expected in a full CIAM client (OAuth PKCE support, refresh tokens, multiple auth flows, etc.). Starting at 0.1.0 accurately reflects the current maturity level.

### Configuration Structure
**Question 4**: How should configuration be structured?
- Option A: Single `Auth0Config` dataclass with all settings
- Option B: Separate config classes (`Auth0Config`, `CookieConfig`, `TimeoutConfig`)
- Option C: Builder pattern with fluent interface
**Answer:** Option A - Single `Auth0Config` dataclass with all settings
**Rationale:** Simplest approach that matches current code patterns and v0.1.0 requirements. Provides good balance of simplicity and flexibility. Can evolve to more complex patterns later if needed as the package matures.

**Detailed Options Analysis:**

**Option A: Single `Auth0Config` dataclass**
```
@dataclass
class Auth0Config:
    base_url: str
    jwt_cookie_names: List[str] = field(default_factory=lambda: ["angel_jwt_v2", "angel_jwt"])
    request_timeout: int = 30
    expiry_buffer_hours: int = 1
    user_agent: Optional[str] = None
```

**Pros:**
- ✅ **Simplicity**: One class to understand and use
- ✅ **Type Safety**: Clear typing with dataclass
- ✅ **Easy to Pass**: Single object for all configuration
- ✅ **Backward Compatible**: Easy to add optional fields
- ✅ **Current Code Alignment**: Matches existing instance variable pattern

**Cons:**
- ❌ **Potential Bloat**: May become cluttered as features grow
- ❌ **All-or-Nothing**: Must provide all required fields at once
- ❌ **Less Modular**: Harder to extend specific config areas independently

**Option B: Separate config classes**
```
@dataclass
class Auth0Config:
    base_url: str

@dataclass
class CookieConfig:
    jwt_cookie_names: List[str] = field(default_factory=lambda: ["angel_jwt_v2", "angel_jwt"])

@dataclass
class TimeoutConfig:
    request_timeout: int = 30
    expiry_buffer_hours: int = 1

@dataclass
class Auth0FullConfig:
    auth: Auth0Config
    cookies: CookieConfig
    timeouts: TimeoutConfig
    user_agent: Optional[str] = None
```

**Pros:**
- ✅ **Modular**: Each concern separated and testable independently
- ✅ **Extensible**: Easy to add new config categories without touching existing code
- ✅ **Clear Organization**: Related settings grouped logically
- ✅ **Optional Composition**: Can use partial configs for different use cases

**Cons:**
- ❌ **Complexity**: Multiple classes to manage and import
- ❌ **Verbose Usage**: More objects to create and pass around
- ❌ **Nested Access**: `config.timeouts.request_timeout` vs `config.request_timeout`
- ❌ **Over-engineering**: May be unnecessary for current simple use case

**Option C: Builder pattern with fluent interface**
```
class Auth0ConfigBuilder:
    def __init__(self):
        self._base_url = None
        self._jwt_cookie_names = ["angel_jwt_v2", "angel_jwt"]
        self._request_timeout = 30
        self._expiry_buffer_hours = 1
        self._user_agent = None

    def base_url(self, url: str) -> 'Auth0ConfigBuilder':
        self._base_url = url
        return self

    def jwt_cookies(self, names: List[str]) -> 'Auth0ConfigBuilder':
        self._jwt_cookie_names = names
        return self

    def timeout(self, seconds: int) -> 'Auth0ConfigBuilder':
        self._request_timeout = seconds
        return self

    def build(self) -> 'Auth0Config':
        if not self._base_url:
            raise ValueError("base_url is required")
        return Auth0Config(
            base_url=self._base_url,
            jwt_cookie_names=self._jwt_cookie_names,
            request_timeout=self._request_timeout,
            expiry_buffer_hours=self._expiry_buffer_hours,
            user_agent=self._user_agent
        )

# Usage: config = Auth0ConfigBuilder().base_url("https://example.com").timeout(60).build()
```

**Pros:**
- ✅ **Fluent API**: Readable, chainable method calls
- ✅ **Optional Configuration**: Only set what you need
- ✅ **Validation**: Can validate at build time
- ✅ **Extensible**: Easy to add new builder methods

**Cons:**
- ❌ **Most Complex**: Significant boilerplate code
- ❌ **Runtime Errors**: Validation happens at runtime, not type checking
- ❌ **Learning Curve**: Users must learn builder pattern
- ❌ **Overkill for Simple Cases**: Unnecessary complexity for basic configuration

### Configurable Settings
**Question 5**: Which settings should be configurable?
- Base URLs (web_url, auth_url, api_url)
- Cookie names (jwt_cookie_names list with priority)
- Timeouts (request_timeout, expiry_buffer_hours)
- User agent string
- Any others
**Answer:** The 4 categories look good. May only need base URL since we should follow redirects rather than hardcoding auth.angel.com. Current implementation assumes flow rather than being fully config-driven.
**Rationale:** Following OAuth/Auth0 best practices of following redirects instead of hardcoding intermediate URLs. This makes the implementation more robust and adaptable to Auth0 configuration changes.

### Dependencies
**Question 7**: Package dependencies?
- Core: `requests`, `beautifulsoup4` (already in Kodi addon)
- Optional: `typing-extensions` for older Python versions
- Test: `pytest`, `pytest-mock`
**Answer:** Python 3+ only, so no typing-extensions needed. pytest and pytest-mock yes, but address packaging structure later.
**Rationale:** Modern Python versions have built-in typing support. Test dependencies can be handled via optional extras or separate test requirements.

### Python Version Support
**Question 8**: Which Python versions to support?
- Kodi addon requires Python 3.8+ (xbmc.python 3.0.1)
- For broader compatibility: 3.7+ or 3.8+
**Answer:** Python 3.8+
**Rationale:** Matches Kodi's minimum requirement and allows use of modern Python features without compatibility concerns.

### Error Handling
**Question 9**: How to handle Auth0-specific errors?
- Keep current exception types but make them more generic
- Add new exceptions for common Auth0 errors (invalid_client, access_denied, etc.)
**Answer:** Align to Auth0 errors as much as possible
**Rationale:** Better interoperability and debugging when users encounter Auth0-specific error conditions. Maintains consistency with Auth0's error response formats.

### Release Strategy
**Question 10**: How to handle the release?
- Release `auth0-ciam` 1.0.0 first, then update Kodi addon
- Release both simultaneously
**Answer:** Release auth0-ciam-client 0.1.0 first, then update Kodi addon. Kodi can continue using local code until auth0-ciam-client is ready.
**Rationale:** Allows testing the package independently before migrating Kodi addon. Provides fallback option if package needs adjustments before Kodi adoption.

### Additional Concerns
**Question 11**: Any other concerns or requirements?
**Answer:** Start new repo for this project. Make plan robust enough to hand off to new instance of GrokCode in new repository. Create sidecar documentation useful for new repo.
**Rationale:** Clean separation of concerns. New repo allows independent development, testing, and versioning. Comprehensive documentation ensures smooth handoff to new development instances.

**Sidecar Documentation Created:**
- `auth0-ciam-client-sidecar-docs.md`: Comprehensive project documentation
- `auth0-ciam-client-implementation-roadmap.md`: 4-week implementation plan

### Makefile Restructuring (Phase 2)
**Decision**: Implement hybrid Makefile approach for coordinated development
- **Root Makefile**: Reorganized with variables, better documentation, coordination targets (`lint-all`, `test-all`)
- **auth0-ciam-client/Makefile**: New standalone Makefile for package development
- **Benefits**: Package can be developed independently while maintaining coordination with Kodi addon
- **Future-ready**: Package Makefile can be copied directly when moving to separate repository

**Root Makefile Features:**
- Variables for maintainability (`ADDON_DIRS`, `PACKAGE_DIR`, etc.)
- Scoped targets (addon-only vs package-only vs coordinated)
- Clear help documentation
- Coordination targets (`lint-all`, `test-all`, `clean-all`)

**Package Makefile Features:**
- Standalone development support
- Uses shared virtual environment (`../.venv`)
- Standard targets: `test`, `lint`, `format`, `build`, `install`, `clean`
- Ready for independent repository migration

## Implementation Phases

### Phase 1: Package Setup ✅ COMPLETE
- [x] Create package directory structure
- [x] Set up setup.py/pyproject.toml
- [x] Configure basic metadata
- [x] Create Auth0Config dataclass with Angel Studios preset
- [x] Implement SessionStore interface and InMemorySessionStore
- [x] Create exception hierarchy
- [x] Set up package __init__.py with API exports

### Phase 2: Core Extraction ✅ COMPLETE
- [x] Extract _perform_authentication method from angel_authentication.py
- [x] Adapt authentication flow to use configurable Auth0Config
- [x] Implement proper error handling with custom exceptions
- [x] Create auth0-ciam-client/Makefile for standalone development
- [x] Create auth0-ciam-client/requirements-dev.txt
- [x] Update root Makefile with hybrid approach and coordination targets
- [x] Format and lint all package code
- [x] Test package functionality and integration

### Phase 3: Testing Migration
- [ ] Move authentication tests to auth0-ciam-client/tests/
- [ ] Update test imports and fixtures
- [ ] Add package-specific integration tests
- [ ] Ensure test coverage maintained

### Phase 4: Documentation
- [ ] Create comprehensive README with usage examples
- [ ] Add API documentation and docstrings
- [ ] Create Angel Studios integration example
- [ ] Update sidecar documentation with implementation details

### Phase 5: Kodi Integration
- [ ] Update Kodi addon imports to use auth0-ciam-client
- [ ] Test compatibility and backward compatibility
- [ ] Update addon.xml dependencies
- [ ] Remove extracted code from angel_authentication.py

## Phase 2 Implementation Details

### Authentication Logic Extraction
- **Source**: `angel_authentication.py:_perform_authentication()`
- **Destination**: `auth0_ciam_client/core.py:AuthenticationCore._perform_authentication()`
- **Adaptations Made**:
  - Replaced hardcoded `self.web_url`/`self.auth_url` with `self.config.base_url`
  - Made cookie names configurable via `config.jwt_cookie_names`
  - Added configurable timeouts and user agents
  - Updated error handling to use custom exception hierarchy
  - Maintained 7-step Auth0 authentication flow logic

### Configuration System
- **Auth0Config**: Single dataclass with all settings (base_url, jwt_cookie_names, request_timeout, expiry_buffer_hours, user_agent)
- **Angel Studios Preset**: `Auth0Config.for_angel_studios()` class method for easy configuration
- **Type Safety**: Full type hints and validation

### Exception Hierarchy
- **Base**: `AuthenticationError`
- **Specific**: `NetworkError`, `InvalidCredentialsError`, `AuthenticationRequiredError`
- **Auth0-Aligned**: Error messages follow Auth0 error response patterns

### Package Structure
```
auth0-ciam-client/
├── auth0_ciam_client/
│   ├── __init__.py      # API exports
│   ├── config.py        # Auth0Config dataclass
│   ├── core.py          # AuthenticationCore implementation
│   ├── exceptions.py    # Custom exception hierarchy
│   └── session_store.py # SessionStore interface + InMemorySessionStore
├── tests/
│   └── __init__.py      # Ready for test migration
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Development dependencies
├── setup.py            # Package configuration
├── README.md           # Package documentation
└── Makefile            # Standalone development targets
```

## Status
**Current Phase:** Phase 2 Complete - Ready for Phase 3 (Testing Migration)
**Decisions Made:** 11/11
**Package Structure:** ✅ Complete (auth0-ciam-client/ directory with full package structure)
**Authentication Logic:** ✅ Extracted and implemented
**Makefile System:** ✅ Hybrid approach implemented
**Testing:** ✅ All existing tests pass (467 tests, 83% coverage)
**Code Quality:** ✅ Formatted and linted
**Ready to Implement:** Phase 3 (Testing Migration)

*Last Updated: January 29, 2026*