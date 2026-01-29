# Auth0 CIAM Client - Implementation Roadmap

## Project Overview & Decisions

### Package Naming
**Decision**: `auth0-ciam-client` - Explicitly indicates this is a client-side implementation for Auth0 CIAM, distinguishing it from server-side tools prevalent on PyPI.

### Licensing
**Decision**: GPL-3.0-only (for now) - Maintains consistency with the current Kodi addon license. Can be adjusted to more permissive license before publishing.

### Versioning
**Decision**: `0.1.0` - Provides basic functionality sufficient for Angel Studios integration, but far from a complete Auth0 CIAM implementation.

### Configuration Structure
**Decision**: Single `Auth0Config` dataclass with all settings - Simplest approach that matches current code patterns and v0.1.0 requirements.

### Configurable Settings
**Decision**: Base URLs, cookie names, timeouts, and user agent string. May only need base URL since we should follow redirects rather than hardcoding auth.angel.com.

### Dependencies
**Decision**: Python 3.8+, requests, beautifulsoup4, pytest, pytest-mock. No typing-extensions needed for modern Python.

### Error Handling
**Decision**: Align to Auth0 errors as much as possible for better interoperability and debugging.

### Release Strategy
**Decision**: Release auth0-ciam-client 0.1.0 first, then update Kodi addon. Allows testing the package independently.

## Current Implementation Status

### ✅ Completed Work
- **Package Structure**: Full `auth0-ciam-client/` directory with complete package structure
- **Authentication Logic**: Extracted and implemented from `angel_authentication.py`
- **Configuration System**: `Auth0Config` dataclass with Angel Studios preset
- **Exception Hierarchy**: Custom exceptions aligned with Auth0 error patterns
- **Makefile System**: Hybrid approach with root coordination and package standalone development
- **Code Quality**: Formatted, linted, and tested (467 tests pass, 83% coverage)

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

## Phase 3: Testing & Documentation (Current Phase)
**Goal**: Comprehensive testing and documentation

### Tasks
- [ ] Migrate authentication tests to `auth0-ciam-client/tests/`
- [ ] Create package-specific unit tests
- [ ] Add configuration-specific tests
- [ ] Create integration tests for end-to-end flows
- [ ] Write comprehensive README with usage examples
- [ ] Create API documentation and docstrings
- [ ] Add Angel Studios integration example
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Ensure 100% test coverage for package code

### Success Criteria
- 100% test coverage maintained for package
- Documentation covers all public APIs
- CI/CD passes on all pushes
- Examples work end-to-end
- Package can be tested independently

## Phase 4: Packaging & Kodi Integration
**Goal**: Prepare for PyPI release and complete Kodi integration

### Tasks
- [ ] Finalize package metadata and dependencies
- [ ] Test PyPI upload process (test.pypi.org)
- [ ] Create release notes and changelog
- [ ] Update Kodi addon to use auth0-ciam-client package
- [ ] Test Kodi integration and backward compatibility
- [ ] Update Kodi addon.xml dependencies
- [ ] Publish v0.1.0 to PyPI
- [ ] Remove extracted code from angel_authentication.py

### Success Criteria
- Package available on PyPI (or test PyPI)
- Kodi addon works with new dependency
- No regressions in functionality
- Backward compatibility maintained
- Documentation accessible online

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

### End of Week 3
- Full test suite passing
- Documentation complete
- CI/CD operational

### End of Week 4
- Package published to PyPI
- Kodi addon updated
- Release announced

---

*This roadmap provides a structured 4-week plan for implementing the auth0-ciam-client package. Adjust timeline as needed based on actual progress and unforeseen issues.*