# Unit Tests README

## Overview

This directory contains unit tests for the Kodi Angel Studios plugin. Tests are organized by module with coverage-specific tests in separate `*_coverage.py` files. All tests use pytest with 100% coverage requirement.

## Test Structure

- `test_<module>.py`: Main behavioral tests for `<module>.py`
- `test_<module>_coverage.py`: Edge case and coverage-specific tests
- `conftest.py`: Shared fixtures and setup
- `unittest_data.py`: Centralized test data constants

## Key Conventions

### Fixtures

- **Naming**: All fixtures prefixed with `mock_` (e.g., `mock_logger`, `mock_kodi_addon`)
- **Scope**: Function-scoped by default for isolation
- **Composition**: High-level fixtures (e.g., `ui_interface`) compose lower-level mocks
- **Teardown**: Generator fixtures include explicit mock resets to prevent state leakage

### Mocking

- **Global Mocks**: Kodi modules patched at import time in `conftest.py`
- **Selective Patching**: Use `patch()` for specific calls, fixtures for common patterns
- **Mock Verification**: Assert calls with `assert_called_once()`, `assert_any_call()`
- **State Isolation**: Mocks reset between tests via teardown

### Parametrization

- Use `@pytest.mark.parametrize` for edge cases and boundaries
- Combine similar tests into parametrized versions
- Include descriptive IDs for clarity

### Coverage

- 100% coverage required (enforced via `make unittest-with-coverage`)
- Coverage-specific tests isolated in `*_coverage.py` files
- Comments explain coverage rationale in docstrings

## Running Tests

```bash
# All tests with coverage
make unittest-with-coverage

# Specific test file
pytest tests/unit/test_kodi_ui_interface.py

# With verbose output
pytest -v tests/unit/
```

## Common Patterns

### Testing UI Methods

```python
def test_projects_menu_success(ui_interface, mock_kodi_xbmcplugin):
    ui, logger, api = ui_interface
    mock_xbmc = mock_kodi_xbmcplugin

    # Setup mocks
    api.get_projects.return_value = [MOCK_PROJECT_DATA["series"]]

    # Execute
    ui.projects_menu()

    # Assert
    mock_xbmc["addDirectoryItem"].assert_called()
    logger.info.assert_called_with("Loaded 1 projects")
```

### Testing Exceptions

```python
def test_method_handles_exception(ui_interface):
    ui, logger, api = ui_interface

    api.some_method.side_effect = Exception(TEST_EXCEPTION_MESSAGE)

    with pytest.raises(Exception, match=TEST_EXCEPTION_MESSAGE):
        ui.some_method()

    logger.error.assert_called()
```

### Parametrized Edge Cases

```python
@pytest.mark.parametrize("input_val, expected", [
    (None, {}),
    ("invalid", {}),
    ({"key": "value"}, {"key": "value"}),
])
def test_normalize_input(input_val, expected):
    result = normalize_function(input_val)
    assert result == expected
```

## Fixtures Reference

- `ui_interface`: Full KodiUIInterface with all dependencies mocked
- `mock_kodi_addon`: Addon settings mock
- `mock_logger`: Logging mock
- `mock_angel_interface`: API client mock
- `mock_simplecache_instance`: Cache mock
- `mock_kodi_xbmcplugin`: Kodi plugin methods mock
- `mock_kodi_xbmcgui`: Kodi GUI methods mock

See `conftest.py` for detailed fixture implementations.