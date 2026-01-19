# Testing Strategy and Norms

**Date:** January 16, 2026
**Status:** Active
**Audience:** Developers, Agents, QA

This document codifies the testing strategy, norms, and best practices for the Kodi Angel Studios plugin. It serves as a guide for both human contributors and AI agents when creating, modifying, or reviewing tests. The goal is to maintain high-quality, maintainable tests that ensure 100% code coverage without behavioral changes.

## Core Principles

- **100% Coverage Non-Negotiable**: All code must be tested. No `# pragma: no cover` or other bypasses without explicit human authorization.
- **Behavioral Testing**: Tests must verify functionality, not just hit lines. Coverage tests should be meaningful.
- **Isolation and Reproducibility**: Tests should run independently and produce consistent results.
- **Readability and Maintainability**: Tests should be clear, well-documented, and easy to update.

## Test Structure and Organization

### File Naming Convention
- `test_<file-being-tested>_<optional-specific-area>.py`
- Examples: `test_kodi_ui_interface_menus.py`, `test_angel_interface_cache.py`
- Place in `tests/unit/` directory.

### Class-Based Organization
- Use descriptive class names mirroring the module (e.g., `TestKodiLogger` for `kodi_utils.py`).
- Group related tests in classes for logical separation.

### Method Naming
- `test_<descriptive_action>` (e.g., `test_router_dispatch_with_valid_action`).
- Use underscores for readability.

## Fixtures and Mocking

### Fixtures (`conftest.py`)
- Use layered fixtures for reuse:
  - Global mocks (e.g., `mock_xbmc`) to isolate Kodi dependencies.
  - Composed fixtures (e.g., `ui_interface`) combining multiple mocks.
- Document all fixtures with complete docstrings explaining purpose, parameters, and return values.
- Prefer fixtures over setup/teardown methods.

### Mocking Patterns
- Patch at module level (e.g., `"xbmcplugin.addDirectoryItem"`) for consistency.
- Return sensible defaults (e.g., empty lists for API failures).
- Avoid over-mocking; patch only what's necessary for the test.
- Use `MagicMock` for complex objects.

### Bad Practice: Over-Mocking
```python
# Avoid: Verbose individual patches
with patch("xbmcplugin.setContent") as mock_set, \
     patch("xbmcplugin.addSortMethod") as mock_sort:
    # Test code
```

### Good Practice: Composed Fixtures
```python
# Prefer: Use fixtures from conftest.py
def test_menu(ui_interface, mock_xbmc):
    # Clean, reusable setup
```

## Test Data Management

### Centralization
- Store test data in `unittest_data.py` as constants (e.g., `MOCK_PROJECT_DATA`).
- Avoid hardcoded strings in tests; reference constants instead.

### Bad Practice: Hardcoded Data
```python
# Avoid
assert result == "http://example.com/"
```

### Good Practice: Centralized Data
```python
# Prefer
from .unittest_data import EXAMPLE_URL
assert result == EXAMPLE_URL
```

## Parametrization and Coverage

### Parametrization
- Use `@pytest.mark.parametrize` extensively for multiple scenarios (e.g., cache hit/miss, content types).
- Include `ids` for clear failure messages.
- Cover happy paths, edge cases, and error conditions.

### Edge Cases
- Integrate edge-case tests into existing files where natural.
- If isolation is needed, create `test_edgecases.py` (rare; prioritize integration to avoid fragmentation).

### Error Handling
- Test exceptions, None/empty responses, and boundary values.
- Verify error dialogs and logging.

## Assertions and Documentation

### Assertions
- Clear and specific (e.g., `assert_called_once_with(args)`).
- Check call arguments, counts, and side effects.

### Docstrings
- Every test method must have a docstring explaining purpose.
- Fixtures in `conftest.py` must have complete docstrings.

### Example Good Test
```python
class TestAngelInterface:
    @pytest.mark.parametrize("cache_hit", [False, True])
    def test_get_project_caching(self, angel_interface_mock, cache_hit):
        """Test project retrieval with cache hit/miss scenarios."""
        # Setup
        # Assertions
```

## Coverage Goals

- Achieve 100% coverage via meaningful tests.
- Use `make unittest-with-coverage` to validate.
- Coverage-specific tests (e.g., in `test_*_coverage.py`) should be integrated into main classes where possible, with comments explaining rationale.

## CI and Validation

- No CI yet; run `make unittest-with-coverage`, `make flake8`, `make black-check` locally.
- All tests must pass before commits.

## Examples of Bad Practices to Avoid

- Unused imports or variables.
- Tests that don't assert behavior.
- Hardcoded values not in `unittest_data.py`.
- Over-patching without fixtures.

## Maintenance

- Update this document as norms evolve.
- Review tests during code changes to ensure conformity.