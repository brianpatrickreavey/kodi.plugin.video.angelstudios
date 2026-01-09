# .github/copilot-instructions.md

## Kodi Plugin for Angel Studios - AI Agent Guidelines

This is a Kodi addon (`plugin.video.angelstudios`) for streaming Angel Studios content. The codebase follows Kodi plugin conventions with custom GraphQL API integration.

### Workflow Practices

- Unless explicit authorization is given to edit code, all requests are to be
  treated as read-only conversations about the codebase, plans, and options.
- Ask for clarification if anything is unclear or multiple approaches are viable.
- Do not interpret questions as invitations to choose and act; questions are questions, directives are directives.
- All proposed code changes should be preceeded by a clear plan and rationale.
- The developer controls the process; defer to their decisions.
- Always re-read all relevant files before making suggestions or changes.  Do NOT rely on cache or other shortcuts.
- Never assume how something works—verify by reading files and documentation.
- Be truthful and factual; avoid anthropomorphism (e.g., do not claim to "misread" files or "forget" actions).
- Prioritize accurate, concise, and direct communication.
- Prioritize correct, robust code; avoid workarounds, shortcuts, or bad patterns.
- Target 100% unit test coverage; do not skip testing any code portions.
- Adhere to best practices; justify any deviations clearly.
- Use test data and parameterization extensively in tests.
- Favor verbose, readable code over clever or obscure implementations.


### Architecture Overview
- **Core Components**:
  - `resources/lib/kodi_ui_interface.py`: Handles Kodi UI interactions (menus, playback, error dialogs). Uses Kodi's `xbmcplugin` and `xbmcgui` for directory listings and video resolution.
  - `resources/lib/angel_interface.py`: Manages GraphQL API calls to Angel Studios, including authentication via `angel_authentication.py`. Caches queries/fragments and handles session validation.
  - `resources/lib/angel_authentication.py`: Handles OAuth-like authentication with session management.
- **Data Flow**: User actions in Kodi trigger UI methods → API calls via `angel_interface` → GraphQL queries → Kodi UI updates. Authentication is checked before API calls.
- **Key Patterns**:
  - **Caching**: Use `SimpleCache` for project data, episode data, and GraphQL responses. Cache keys like `project_{slug}` or `episode_data_{guid}_{slug}`.
  - **Error Handling**: Methods return `None`/`{}` on failures; UI shows dialogs via `show_error()`.
  - **File Loading**: GraphQL queries/fragments loaded from `resources/graphql/` with caching in `_query_cache`/`_fragment_cache`.

### Developer Workflows
- **Testing**: Run `pytest --cov=kodi_ui_interface --cov-report=html` from project root. Tests use fixtures in `tests/unit/conftest.py` for mocking Kodi (`xbmcplugin`, `xbmcgui`) and sessions.
- **Debugging**: Use Kodi's log viewer for addon logs. Mock external calls in tests to isolate issues.
- **Build/Deploy**: No custom build; install as Kodi addon. Use `addon.xml` for metadata.

### Code Style
- For multiple `unittest.mock.patch` context managers, prefer parenthesized `with` blocks instead of line continuations. Example:
  ```python
  with (
      patch('xbmcaddon.Addon', return_value=addon),
      patch('xbmcgui.ListItem', return_value=list_item),
  ):
      ...
  ```
- Prefer addon detection with `xbmc.getCondVisibility('System.HasAddon(<addon_id>)')` over try/except import patterns when checking for optional plugins.

### Project Conventions
- **Imports**: Use relative imports for lib modules (e.g., `from .unittest_data import MOCK_PROJECT_DATA`).
- **Mocking**: Patch Kodi modules at `xbmcplugin.*` or `xbmcgui.*`. Use `MagicMock` for sessions/auth.
- **Parametrization**: Test multiple scenarios (e.g., cache hit/miss) with `@pytest.mark.parametrize`.
- **File Structure**: Tests mirror lib structure (`test_kodi_ui_interface.py` for `kodi_ui_interface.py`). Fixtures in `conftest.py` shared across test files.
- **Settings schema**: `resources/settings.xml` uses the version="1" format; all implementation details
are available here: https://kodi.wiki/view/Add-on_settings_conversion
- **Examples**:
  - UI tests: `with patch('xbmcplugin.setResolvedUrl') as mock_resolve: ui.play_video(...)`
  - API tests: Mock `session.post` for GraphQL; assert `return_value == {}` on errors.

### Integration Points
- **External Dependencies**: `requests` for HTTP, `simplecache` for caching, Kodi APIs.
- **Cross-Component**: UI calls `angel_interface.get_project()`; auth session shared via `AngelStudioSession`.
- **Patterns**: Always check `session_check()` before API calls; handle GraphQL errors by returning `{}`.

Reference `tests/unit/conftest.py` for fixture examples and `resources/lib/kodi_ui_interface.py` for UI patterns.

---

Please provide feedback on any unclear or incomplete sections to iterate.
