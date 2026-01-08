# Continue Watching Feature

## Overview
Add a new "Continue Watching" menu item that displays in-progress episodes from the Angel API using cursor-based pagination with a deliberate "Load More" button. As part of this work, apply native Kodi progress indicators to all episode/content list items across the plugin.

## Feature Scope

### Continue Watching Menu
- **Main Menu Item**: New "Continue Watching" option in main menu (toggleable via addon settings)
- **Display**: List of in-progress episodes with native progress bars
- **Dynamic Loading**: Initial load shows first batch (~10-25 items), "Load More" button appends next batch
- **Load More**: Button labeled "Load more in-progress content" at end of list
- **No Caching**: Always fetch fresh data to reflect current watch progress
- **Empty State**: Show menu item "No in-progress content found!" with generic back action to return to previous menu

### Global Progress Bar Enhancement
- Apply native Kodi progress indicators (`setResumePoint()`) to **all** episode/content lists:
  - `episodes_menu()` - display progress on each episode
  - `seasons_menu()` - display progress if episodes are shown
  - `continue_watching_menu()` - display progress on resume content
  - Any other content list items where watch data is available
- Shows visual progress overlay on thumbnails when available

## Technical Implementation Plan

### Phase 1: Global Progress Bar Enhancement

#### 1.1 Create Progress Bar Helper
- **Location**: `resources/lib/kodi_ui_interface.py`
- **Method**: `_apply_progress_bar(list_item, watch_position_seconds, duration_seconds)`
- **Purpose**: Centralized method to apply native Kodi resume point to a ListItem
- **Implementation**:
  ```python
  def _apply_progress_bar(self, list_item, watch_position_seconds, duration_seconds):
      """Apply native Kodi resume point to a ListItem."""
      if watch_position_seconds is None or duration_seconds is None or duration_seconds == 0:
          return
      
      info_tag = list_item.getVideoInfoTag()
      resume_point = watch_position_seconds / duration_seconds
      info_tag.setResumePoint(resume_point)
  ```

#### 1.2 Refactor Episode List Methods
- **`episodes_menu()`**: Apply progress bars to each episode using helper
- **`seasons_menu()`**: Apply progress bars if episodes are displayed
- **Other methods**: Search for any other list item creation that has watch data; apply progress bars

#### 1.3 Add Unit Tests
- Test `_apply_progress_bar()` helper with various inputs (valid, edge cases, None values)
- Test that `episodes_menu()` applies progress bars correctly
- Test that list methods handle missing/None watch data gracefully
- Use parametrization for different watch position scenarios

#### 1.4 Commit
- Message: `feat: add native Kodi progress indicators to all content lists`
- Includes helper, refactored methods, and tests

---

### Phase 2: Continue Watching Feature

#### 2.1 Create GraphQL Query
- **File**: `resources/lib/angel_graphql/query_resumeWatching.graphql`
- **Content**: Provided ResumeWatching query with cursor-based pagination

#### 2.2 Add API Method
- **File**: `resources/lib/angel_interface.py`
- **Method**: `get_resume_watching(first: int = None, after: str = None) -> dict`
- **Features**:
  - Accept `first` (page size) and `after` (cursor) parameters
  - Query ResumeWatching GraphQL endpoint
  - Return parsed response with edges, pageInfo, or empty dict on error
  - **No caching** - always fetch fresh API data

#### 2.3 Add Continue Watching UI
- **File**: `resources/lib/kodi_ui_interface.py`
- **Method**: `continue_watching_menu(after: str = None)`
- **Features**:
  - Accept optional `after` cursor parameter for pagination
  - Call `angel_interface.get_resume_watching(after=after)`
  - Handle empty list: add single menu item "No in-progress content found!" with generic back action
  - Format episodes as: "Project Name S##E##: Episode Name" (or appropriate fallback for specials/movies)
  - Apply progress bars to each item using progress bar helper
  - If `pageInfo.hasNextPage == True`: add "Load more in-progress content" menu item at end
  - If `pageInfo.hasNextPage == False`: don't add "Load More" item
  - Handle API errors gracefully (show error dialog, keep existing items visible)

#### 2.4 Add No-Op Return Handler
- **Method**: `no_op_return()` in `kodi_ui_interface.py`
- **Purpose**: Generic back/return action for menu items without specific destinations
- **Implementation**: Kodi plugin URL that performs no action, allowing user to navigate back

#### 2.5 Update Main Menu
- **File**: `resources/lib/kodi_ui_interface.py`
- **Method**: `main_menu()`
- **Change**: Add "Continue Watching" menu item if addon setting enabled

#### 2.6 Add Addon Setting
- **File**: `resources/settings.xml`
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
User clicks "Continue Watching"
    ↓
continue_watching_menu(after=None)
    ↓
get_resume_watching(first=default, after=None)
    ↓
GraphQL ResumeWatching query
    ↓
Parse response, apply progress bars
    ↓
If empty: show "No in-progress content found!"
If has content: display episodes with progress bars
If hasNextPage: add "Load more in-progress content"
    ↓
User clicks "Load more in-progress content"
    ↓
continue_watching_menu(after=<endCursor>)
    ↓
[cycle repeats with next batch]
```

---

## Edge Cases & Error Handling

1. **Empty Continue Watching List**
   - Show "No in-progress content found!" menu item
   - Include back action to return to main menu

2. **API Error on Initial Load**
   - Show error dialog
   - Return to previous menu
   - Do not show any items

3. **API Error on "Load More"**
   - Show error dialog
   - Keep existing items visible
   - Remove "Load More" button (user must retry or return)

4. **Network Timeout**
   - Handle with graceful error dialog
   - Follow same pattern as other API error handling

5. **Mixed Content Types**
   - Episodes: format as "Project Name S##E##: Episode Name"
   - Specials: format as "Project Name: Special Name"
   - Movies: format as "Project Name: Movie Name"
   - Verify all have duration and watch position data

6. **Missing Watch Data**
   - If `duration` or `watchPosition` is None/null, skip progress bar
   - Still display item with available data

---

## Files Modified/Created

### Phase 1
- **Modify**: `resources/lib/kodi_ui_interface.py` (add helper, refactor methods)
- **Create/Modify**: `tests/unit/test_kodi_ui_interface.py` (add progress bar tests)

### Phase 2
- **Create**: `resources/lib/angel_graphql/query_resumeWatching.graphql`
- **Modify**: `resources/lib/angel_interface.py` (add API method)
- **Modify**: `resources/lib/kodi_ui_interface.py` (add UI method, main menu update)
- **Modify**: `resources/settings.xml` (add setting)
- **Create/Modify**: Test files (add comprehensive tests)

---

## Testing Strategy

- **100% test coverage** for all new/modified methods
- **Parametrized tests** for pagination cursors, empty responses, error scenarios
- **Mock all external calls**: Kodi UI functions, GraphQL responses, API errors
- **Edge case testing**: None values, empty strings, very long episode names, very large pages
- **Error scenario testing**: Network timeouts, API errors, malformed responses

---

## Notes

- Progress bar native support relies on `xbmcgui.ListItem.getVideoInfoTag().setResumePoint()`
- ResumePoint expects a float between 0.0 and 1.0 (calculated as position/duration)
- "Load More" button uses explicit menu item, not infinite scroll
- No pagination state is persisted; each menu load is independent
- Always fetch fresh Continue Watching data (no caching) to reflect real-time watch progress
