 # Continue Watching Feature

## Overview
The Continue Watching feature displays in-progress episodes from the Angel API using cursor-based pagination. Progress indicators are applied to all episode/content list items across the plugin using a unified ListItem builder.

## Current Implementation Status

### ✅ Completed Features
- **Main Menu Item**: "Continue Watching" option in main menu (toggleable via addon settings)
- **Display**: List of in-progress episodes with native Kodi progress bars
- **Pagination**: "Load More" button for additional content batches
- **Progress Bars**: Native Kodi resume indicators on all episode lists
- **Unified Builder**: Single `_build_list_item_for_content()` method handles progress bar application
- **Error Handling**: Graceful handling of API errors and empty states

### Technical Implementation

#### Continue Watching Menu
- **Method**: `continue_watching_menu(after=None)` in `KodiMenuHandler`
- **API Call**: `angel_interface.get_resume_watching(first=10, after=after)`
- **Progress Bars**: Applied via `overlay_progress=bool(episode.get("watchPosition"))` in unified builder
- **Pagination**: "Load More..." button when `pageInfo.hasNextPage == True`
- **Empty State**: Shows notification "No items in Continue Watching" when no episodes found
- **Error Handling**: Shows error dialog on API failure

#### Progress Bar Implementation
- **Method**: `_apply_progress_bar()` in `MenuUtils` (consolidated from `KodiMenuHandler`)
- **Input Handling**: Accepts both numeric seconds and `{"position": seconds}` dict format
- **Application**: `info_tag.setResumePoint(resume_point)` where `resume_point = position / duration`
- **Unified Builder**: `_build_list_item_for_content()` applies progress bars when `overlay_progress=True`

#### Episode Formatting
- **Series Episodes**: "Episode Name (Project Name - S##E##)" format
- **Fallback**: "Episode Name (Project Name)" for episodes without season/episode numbers
- **Specials/Movies**: Standard title formatting via unified builder

## Technical Implementation Plan

### Phase 1: Global Progress Bar Enhancement (✅ Completed)

#### 1.1 Create Progress Bar Helper (✅ Consolidated)
- **Location**: `resources/lib/menu_utils.py` (moved from `kodi_ui_interface.py`)
- **Method**: `_apply_progress_bar(list_item, watch_position_data, duration_seconds)`
- **Purpose**: Centralized method to apply native Kodi resume point to a ListItem
- **Features**:
  - Handles both numeric seconds and `{"position": seconds}` dict format
  - Validates input data and logs warnings for invalid structures
  - Calculates `resume_point = position / duration` and clamps to [0.0, 1.0]

#### 1.2 Unified ListItem Builder (✅ Implemented)
- **Location**: `resources/lib/menu_utils.py`
- **Method**: `_build_list_item_for_content(content, content_type_str, **options)`
- **Features**:
  - Single builder for all content types (episodes, projects, seasons)
  - Progress bar application via `overlay_progress=True` option
  - Automatic progress detection: `overlay_progress=bool(content.get("watchPosition"))`
  - Consistent metadata processing and artwork handling

#### 1.3 Refactor Episode List Methods (✅ Completed)
- **`episodes_menu()`**: Uses unified builder with `overlay_progress` option
- **`continue_watching_menu()`**: Uses unified builder with automatic progress detection
- **Inheritance**: `KodiMenuHandler` inherits from `MenuUtils` for shared functionality

#### 1.4 Unit Tests (✅ Maintained)
- Test `_apply_progress_bar()` with dict and numeric inputs
- Test unified builder progress bar application
- Test edge cases: missing position, invalid data, None values
- All tests pass with 88% coverage maintained

---

### Phase 2: Continue Watching Feature (✅ Completed)

#### 2.1 GraphQL Query (✅ Exists)
- **File**: `resources/lib/angel_graphql/query_resumeWatching.graphql`
- **Content**: ResumeWatching query with cursor-based pagination

#### 2.2 API Method (✅ Implemented)
- **File**: `resources/lib/angel_interface.py`
- **Method**: `get_resume_watching(first: int = 10, after: str = None) -> dict`
- **Features**:
  - Cursor-based pagination with `first` and `after` parameters
  - Returns parsed response with episodes and pageInfo
  - No caching - always fetches fresh data
  - Error handling returns empty dict

#### 2.3 Continue Watching UI (✅ Implemented)
- **File**: `resources/lib/kodi_menu_handler.py`
- **Method**: `continue_watching_menu(after: str = None)`
- **Features**:
  - Pagination support with cursor parameter
  - Episode formatting: "Episode Name (Project Name - S##E##)"
  - Progress bars via unified builder
  - "Load More..." button when `pageInfo.hasNextPage == True`
  - Empty state handling with user notification
  - Error handling with dialog display

#### 2.4 Main Menu Integration (✅ Implemented)
- **File**: `resources/lib/kodi_menu_handler.py`
- **Method**: `main_menu()`
- **Features**: Includes "Continue Watching" option when enabled

#### 2.5 Addon Setting (✅ Implemented)
- **File**: `resources/settings.xml`
- **Setting**: `show_continue_watching` boolean toggle
- **Default**: `true` (enabled)
- **Label**: "Show Continue Watching in main menu"

#### 2.6 Plugin URL Routing (✅ Implemented)
- Routes `action=continue_watching_menu` with optional `after` parameter
- Example: `plugin://plugin.video.angelstudios/?action=continue_watching_menu&after=<cursor>`

#### 2.7 Unit Tests (✅ Comprehensive)
- Test pagination, empty states, error handling
- Test progress bar application
- Parametrized tests for different scenarios
- 88% test coverage maintained
- **Setting**: Boolean toggle for "Continue Watching" in main menu
- **Default**: `true` (enabled)
- **Category**: Menu/Display settings

#### 2.7 Add Plugin URL Route
- Update `__init__.py` or main entry point to route `action=continue_watching_menu` with optional `after` parameter
- Example URL: `plugin://plugin.video.angelstudios/?action=continue_watching_menu&after=<cursor>`

#### 2.8 Add Unit Tests
- Test `get_resume_watching()` with:
  - Initial load (no cursor)
  - Pagination with cursor
  - Empty response
  - API errors
  - Missing fields in response
- Test `continue_watching_menu()` with:
  - First batch of items
  - Pagination with Load More
  - Empty list (no in-progress content)
  - API error handling
  - Progress bar application
- Use parametrization for different pagination scenarios

#### 2.9 Commit
- Message: `feat: add Continue Watching menu with pagination`
- Includes GraphQL query, API method, UI method, settings, and tests

---

## Data Flow

```
User clicks "Continue Watching" (if enabled in settings)
    ↓
continue_watching_menu(after=None)
    ↓
get_resume_watching(first=10, after=None)
    ↓
GraphQL ResumeWatching query
    ↓
Parse response: episodes[], pageInfo{hasNextPage, endCursor}
    ↓
For each episode:
    Create episode_display copy with formatted subtitle
    Call _build_list_item_for_content() with overlay_progress=True
    _apply_progress_bar() extracts position from watchPosition dict
    Add to Kodi directory
    ↓
If pageInfo.hasNextPage: add "[Load More...]" item
    ↓
User clicks "[Load More...]"
    ↓
continue_watching_menu(after=<endCursor>)
    ↓
[cycle repeats with next batch]
```

---

## Edge Cases & Error Handling

1. **Empty Continue Watching List**
   - Show notification: "No items in Continue Watching"
   - Return to previous menu (no items displayed)

2. **API Error on Initial Load**
   - Show error dialog: "Failed to load Continue Watching"
   - Return to previous menu

3. **API Error on "Load More"**
   - Show error dialog
   - Keep existing items visible
   - Allow user to retry or return

4. **Missing Watch Position Data**
   - Progress bars only applied when `episode.get("watchPosition")` exists
   - Items still display normally without progress indicators

5. **Invalid Watch Position Format**
   - `_apply_progress_bar()` validates dict structure
   - Logs warning for invalid data, skips progress bar application
   - Item still displays normally

6. **Episode Formatting Edge Cases**
   - Episodes without season/episode numbers: "Episode Name (Project Name)"
   - Episodes without project: standard title formatting
   - Very long titles: handled by Kodi UI truncation

---

## Files Modified/Created

### Phase 1 (Progress Bars)
- **Create**: `resources/lib/menu_utils.py` (unified ListItem builder with progress bar support)
- **Modify**: `resources/lib/kodi_menu_handler.py` (inherit from MenuUtils, use unified builder)
- **Modify**: `resources/lib/menu_utils.py` (consolidate `_apply_progress_bar()` method)
- **Create/Modify**: Test files (progress bar tests with dict input handling)

### Phase 2 (Continue Watching)
- **Create**: `resources/lib/angel_graphql/query_resumeWatching.graphql`
- **Modify**: `resources/lib/angel_interface.py` (add `get_resume_watching()` API method)
- **Modify**: `resources/lib/kodi_menu_handler.py` (add `continue_watching_menu()` UI method)
- **Modify**: `resources/settings.xml` (add `show_continue_watching` boolean setting)
- **Create/Modify**: Test files (comprehensive pagination and error handling tests)

---

## Testing Strategy

- **88% test coverage** maintained for all modified methods
- **Parametrized tests** for pagination cursors, empty responses, error scenarios
- **Mock all external calls**: Kodi UI functions, GraphQL responses, API errors
- **Progress bar testing**: Dict input handling, invalid data validation, edge cases
- **Edge case testing**: None values, missing dict fields, malformed API responses
- **Error scenario testing**: API errors, network timeouts, invalid watch position data

## Notes

- **Progress Bar Implementation**: Uses `xbmcgui.ListItem.getVideoInfoTag().setResumePoint()`
- **Resume Point Calculation**: `position / duration` clamped to [0.0, 1.0] range
- **Watch Position Format**: Handles both legacy numeric and current `{"position": seconds}` dict formats
- **Unified Builder**: Single `_build_list_item_for_content()` method for all content types
- **Pagination**: "Load More..." button with explicit cursor handling
- **No State Persistence**: Each menu load fetches fresh data independently
- **Error Resilience**: Invalid progress data logs warnings but doesn't break item display
- Always fetch fresh Continue Watching data (no caching) to reflect real-time watch progress
