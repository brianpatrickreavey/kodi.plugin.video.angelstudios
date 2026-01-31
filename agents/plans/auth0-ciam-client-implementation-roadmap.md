# Auth0 CIAM Client - Implementation Roadmap

## Project Overview & Decisions

### Package Naming
**Decision**: `auth0-ciam-client` - Explicitly indicates this is a client-side implementation for Auth0 CIAM, distinguishing it from server-side tools prevalent on PyPI.

### Licensing
**Decision**: GPL-3.0-only (for now) - Maintains consistency with the current Kodi addon license. Can be adjusted to more permissive license before publishing.

### Versioning
**Decision**: `0.2.0` - Provides complete functionality for Angel Studios integration with custom JWT decoding, comprehensive testing, and production-ready Kodi integration.

### Configuration Structure
**Decision**: Single `Auth0Config` dataclass with all settings - Simplest approach that matches current code patterns and v0.1.0 requirements.

### Configurable Settings
**Decision**: Base URLs, cookie names, timeouts, and user agent string. May only need base URL since we should follow redirects rather than hardcoding auth.angel.com.

### Dependencies
**Decision**: Python 3.8+, requests, beautifulsoup4, pytest, pytest-mock. No typing-extensions needed for modern Python.

### Error Handling
**Decision**: Align to Auth0 errors as much as possible for better interoperability and debugging.

### Release Strategy
**Decision**: Internal use only for now. PyPI publication deferred until v1.0.0 when broader Auth0 compatibility is implemented.

## Current Implementation Status

### ✅ Completed Work
- **Package Structure**: Full `auth0-ciam-client/` directory with complete package structure
- **Authentication Logic**: Extracted and implemented from `angel_authentication.py` with custom JWT decoding
- **Configuration System**: `Auth0Config` dataclass with Angel Studios preset
- **Exception Hierarchy**: Custom exceptions aligned with Auth0 error patterns
- **Makefile System**: Hybrid approach with root coordination and package standalone development
- **Kodi Integration**: Package bundled as dependency, full functionality working
- **Code Quality**: Formatted, linted, and tested (463 Kodi tests + 43 package tests pass, 86% overall coverage)
- **Test Suite**: Package-specific tests migrated and running (82% package coverage)
- **Documentation**: Comprehensive README with installation, quick start, and API examples
- **Bug Fixes**: Resolved auth URL construction bug preventing "auth.auth.angel.com" DNS errors

### ✅ All Phases Complete
- **Phase 3 (Testing & Documentation)**: 100% complete - Package tests migrated, comprehensive docs, 82% coverage
- **Phase 4 (Packaging & Kodi Integration)**: 100% complete - Full integration working, all tests passing

### 🎯 Ready for Internal Use
- Package version: `0.2.0`
- Kodi addon: Fully functional with bundled dependency
- Authentication: Working correctly with custom JWT handling
- Testing: Comprehensive coverage maintained
- Documentation: Complete and ready for internal reference

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

### Makefile Restructuring
- **Root Makefile**: Reorganized with variables, coordination targets (`lint-all`, `test-all`)
- **Package Makefile**: Standalone development support using shared virtual environment
- **Benefits**: Package can be developed independently while maintaining coordination

## Phase 3: Testing & Documentation (COMPLETE - 100% Done)
**Goal**: Comprehensive testing and documentation

### ✅ Completed Tasks
- Package-specific test suite (43 tests passing, 82% coverage in `auth0_ciam_client/tests/`)
- Test migration from Kodi addon to package completed
- Comprehensive README with installation, quick start, and API examples
- Full API documentation with docstrings throughout
- Angel Studios integration examples included

### Success Criteria - ACHIEVED
- ✅ 82% test coverage maintained for package (43/43 tests passing)
- ✅ Documentation covers all public APIs
- ✅ Examples work end-to-end
- ✅ Package can be tested independently

## Phase 4: Packaging & Kodi Integration (COMPLETE - 100% Done)
**Goal**: Prepare for PyPI release and complete Kodi integration

### ✅ Completed Tasks
- Package structure and metadata finalized (v0.2.0)
- Kodi addon integration working perfectly (bundled dependency)
- All authentication flows working (custom JWT decoding, session management)
- Backward compatibility maintained (no regressions)
- 463 Kodi tests + 43 package tests all passing
- Dependencies properly gitignored and bundled

### Success Criteria - ACHIEVED
- ✅ Kodi addon works with new dependency (menus loading correctly)
- ✅ No regressions in functionality (all tests passing)
- ✅ Backward compatibility maintained (existing features work)
- ✅ Package ready for internal use (v0.2.0)

## Implementation Complete ✅

**Final Status**: Both Phase 3 (Testing & Documentation) and Phase 4 (Packaging & Kodi Integration) are now 100% complete.

**Key Achievements**:
- Package v0.2.0 ready for internal use
- 43 package tests + 463 Kodi integration tests all passing
- Custom JWT decoding working without external dependencies
- Full Kodi addon functionality restored
- Comprehensive documentation and examples
- Clean separation between dedicated repo and bundled dependency

**Interdependency Resolution**: The simultaneous work approach successfully resolved the phase dependencies. Integration testing revealed and fixed critical bugs (like the auth URL construction issue), while package testing ensured API stability.

## Risk Mitigation

### Technical Risks
- **Auth0 Flow Changes**: Monitor for breaking changes, have fallback mechanisms
- **Dependency Conflicts**: Test with multiple Python versions, use specific versions
- **Kodi Compatibility**: Maintain backward compatibility during transition

### Process Risks
- **Timeline Slippage**: Break work into small, testable chunks
- **Quality Issues**: Maintain high test coverage, code review process
- **Documentation Gaps**: Write docs alongside code, validate with examples

## Dependencies

### External Dependencies
- **requests**: HTTP client (already in Kodi)
- **beautifulsoup4**: HTML parsing (already in Kodi)
- **pytest**: Testing framework
- **pytest-mock**: Mocking support

### Internal Dependencies
- **Kodi addon**: For initial testing and integration
- **Angel Studios account**: For end-to-end testing
- **PyPI account**: For package publishing

## Success Metrics

### Code Quality
- 100% test coverage
- No pylint/flake8 errors
- Type hints throughout
- Clear documentation strings

### Functionality
- All existing Angel Studios features work
- Configuration is flexible and well-documented
- Error handling is robust
- Performance is maintained

### Adoption
- Kodi addon successfully migrates
- Package can be imported and used independently
- Documentation enables easy adoption
- Community feedback is positive

## Weekly Checkpoints

### End of Week 1
- Package structure created
- Core classes extracted
- Basic tests passing

### End of Week 2
- Configuration system working
- Angel Studios integration tested
- API stabilized

### End of Week 3 - ACHIEVED
- ✅ Full test suite passing (43 package + 463 Kodi tests)
- ✅ Documentation complete (comprehensive README)
- ✅ CI/CD operational (tests run successfully)

### End of Week 4 - ACHIEVED (Internal Use)
- ✅ Package ready for internal use (v0.2.0)
- ✅ Kodi addon updated and working
- ✅ PyPI publication deferred until v1.0.0

## Phase 5: Enhancements & Future Improvements (v1.0.0+)
**Goal**: Add robustness and advanced features for broader Auth0 compatibility

**Current Status**: Package is production-ready for Angel Studios use. PyPI publication and broader Auth0 compatibility features deferred until v1.0.0.

### Planned Enhancements (Future v1.0.0)

### Planned Enhancements
- [ ] **Dynamic Auth URL Discovery**: Follow login redirects instead of assuming auth subdomain pattern
  - **Benefit**: Works with any Auth0 CNAME configuration (angelstudios.us.auth0.com, login.angel.com, etc.)
  - **Implementation**: Follow redirect from `/auth/login` to discover actual Auth0 domain
  - **Impact**: Makes package compatible with any Auth0 tenant configuration

- [ ] **Enhanced Cookie Handling**: More flexible JWT token extraction
  - **Current**: Configurable cookie name list with priority
  - **Enhancement**: Support regex patterns, domain-specific cookies, fallback strategies
  - **Benefit**: Handles edge cases in Auth0 cookie naming

- [ ] **OAuth PKCE Support**: Add proper OAuth 2.0 PKCE flow as alternative
  - **Benefit**: More secure and standard authentication method
  - **Implementation**: When available, use PKCE instead of web scraping
  - **Fallback**: Maintain current scraping approach for legacy Auth0 setups

- [ ] **Token Refresh Support**: Implement OAuth refresh tokens
  - **Benefit**: Seamless token renewal without re-authentication
  - **Implementation**: Store and use refresh tokens when available
  - **Impact**: Better user experience for long sessions

### Success Criteria
- Package works with any Auth0 tenant configuration
- Multiple authentication methods supported
- Enhanced security and user experience
- Backward compatibility maintained

---

*This roadmap provides a structured plan for implementing the auth0-ciam-client package. Phase 5 enhancements can be implemented in future versions (0.2.0+) after initial release.*