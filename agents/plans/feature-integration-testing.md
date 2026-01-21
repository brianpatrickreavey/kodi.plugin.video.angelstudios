# Feature: Integration Testing

**Date:** January 21, 2026
**Status:** Planning
**Owner:** Architecture & Product
**Audience:** Developer, QA

---

## Executive Summary

This feature implements integration tests for the Kodi Angel Studios plugin to validate end-to-end user flows using real API calls with dedicated test credentials. The focus is on testing full application stacks while mocking only external dependencies. Investigation into Kodi integration testing methods (Docker, RPC calls) is required.

**Scope:**
- Create `tests/integration/` with comprehensive flow tests
- Investigate Kodi testing approaches (Docker containers, RPC calls)
- Use real HTTP calls for Angel Studios API
- Mock Kodi UI and file system

**Risk Profile:** Medium (external dependencies)

**Timeline Estimate:** 6-8 hours

**Success Criteria:**
1. Integration tests validate full user flows
2. Test credentials securely managed
3. Kodi testing method established
4. CI/CD integration for automated execution

---

## Investigation: Kodi Integration Testing Methods

### Options to Explore

1. **Docker-based Testing:**
   - Run Kodi in Docker container
   - Use X11 forwarding or headless mode
   - Mount plugin code as volume
   - Simulate user interactions via scripts

2. **RPC Calls:**
   - Use Kodi's JSON-RPC API for remote control
   - Send commands to running Kodi instance
   - Monitor responses and UI state
   - Requires running Kodi instance

3. **Mock-heavy Unit Tests:**
   - Deep mocking of Kodi components
   - Test logic flows without real Kodi
   - Limited to component interaction validation

4. **Hybrid Approach:**
   - Unit tests for components
   - Integration tests for API flows
   - Manual testing for full UI flows

### Recommended Investigation Steps

1. Research existing Kodi addon testing frameworks
2. Set up Docker environment with Kodi
3. Test RPC API capabilities
4. Prototype simple integration test
5. Evaluate feasibility and maintenance cost

---

## Implementation Plan

### 1. Set Up Test Infrastructure

**Action:**
1. Create `tests/integration/` directory
2. Configure test credentials (`test_credentials_integration.json`)
3. Set up Docker/Kodi environment if feasible
4. Implement RPC client if using RPC approach

### 2. Implement Flow Tests

**Test Scenarios:**
- Project browsing → Episode selection → Playback
- Continue watching → Resume playback
- Cache hit/miss scenarios
- Error handling (network failures, invalid responses)

**Example Test:**
```python
def test_project_browse_to_playback():
    # Setup Kodi mock/RPC connection
    # Navigate to projects menu
    # Select project, season, episode
    # Verify playback initiated
    # Assert metadata and URL correct
```

### 3. Mock Strategy

**Mock Boundaries:**
- Kodi UI components (`xbmcplugin`, `xbmcgui`)
- File system operations
- External addons
- Real: HTTP requests to Angel Studios API

### 4. CI/CD Integration

**Action:**
1. Add integration test pipeline
2. Run nightly or on-demand
3. Use dedicated test environment
4. Monitor for flakiness

---

## Acceptance Criteria

- [ ] Integration test suite implemented
- [ ] Kodi testing method established and documented
- [ ] Full user flows validated
- [ ] Test credentials isolated
- [ ] CI/CD pipeline includes integration tests

---

## Configuration

### pytest.ini Updates
```ini
[pytest]
testpaths = tests/unit tests/integration
markers =
    integration: marks integration tests
```

### Makefile Updates
```makefile
integration-tests:
	pytest tests/integration/ -m integration
```

---

## Progress Tracking

- [ ] Investigate Kodi testing methods
- [ ] Set up test infrastructure
- [ ] Implement core flow tests
- [ ] Configure CI/CD
- [ ] Validate and document approach

---

## Risk Mitigation

**Risk:** Tests flaky due to external dependencies
**Mitigation:** Retry logic, dedicated environment, separate execution

**Risk:** Kodi testing complex to set up
**Mitigation:** Start with simpler mocking, escalate if needed

---

## File Changes

- **New:** `tests/integration/` directory
- **New:** Integration test files
- **Modified:** `pytest.ini`, `Makefile`
- **New:** `test_credentials_integration.json`