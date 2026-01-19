# GROK-ART-REGRESSION-FIX.md

## Overview
Fixed the artwork regression where STILL images were not appearing as posters in Kodi for ContentSeries projects and episodes. This was a critical issue affecting the visual presentation of animated shows like Tuttle Twins, Wingfeather Saga, and others.

## Problem Statement
- STILL images (portraitTitleImage for projects, portraitStill1 for episodes) were being fetched from Angel Studios API but not displayed in Kodi
- Kodi was falling back to discoveryPosterCloudinaryPath instead of using the higher-quality STILL images
- This affected both main menus (project posters) and episode lists (episode posters)

## Root Cause Analysis
1. **GraphQL Queries**: STILL fields were missing from queries
2. **Data Merging**: STILL images for episodes weren't being merged from project data
3. **Artwork Mapping**: STILL images weren't being prioritized in Kodi artwork setting
4. **Nested Access**: STILL images for projects were nested under `title` but code only checked top-level

## Solution Implementation

### Phase 1: GraphQL Query Updates
- **File**: `plugin.video.angelstudios/resources/lib/angel_graphql/query_getProject.graphql`
- **Change**: Added STILL fields (portraitStill1-3, landscapeStill1-3) for ContentSeries episodes
- **File**: `plugin.video.angelstudios/resources/lib/angel_graphql/query_getProjectsForMenu.graphql`
- **Change**: Confirmed STILL fields available (portraitTitleImage, etc.)

### Phase 2: Data Merging Logic
- **File**: `plugin.video.angelstudios/resources/lib/angel_interface.py`
- **Changes**:
  - Added `_merge_episode_data()` to merge STILL images into episodes
  - Added debug logging for ContentSeries detection
  - Ensured STILL fields are flattened to top-level for episodes

### Phase 3: Artwork Priority Logic
- **File**: `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
- **Changes**:
  - Updated `_process_attributes_to_infotags()` to prioritize STILL images
  - Added nested access for project STILLs (under `title`)
  - Set poster to `portraitTitleImage` for projects, `portraitStill1` for episodes
  - Maintained fallbacks to discovery images

### Phase 4: Testing and Validation
- **Tests**: All 344 unit tests pass with 97% coverage
- **Validation**: Kodi logs confirmed STILL images now being set as posters
- **Verification**: User confirmed improved artwork display in Kodi interface

## Files Modified
- `plugin.video.angelstudios/resources/lib/angel_graphql/query_getProject.graphql`
- `plugin.video.angelstudios/resources/lib/angel_interface.py`
- `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
- `docs/artwork_mapping.md` (new documentation)

## Key Technical Details
- **STILL Priority**: portraitTitleImage > portraitStill1 > discoveryPosterCloudinaryPath
- **Landscape Priority**: landscapeStill1 > discoveryPosterLandscapeCloudinaryPath
- **Data Structure**: Projects have STILLs nested in `title`, episodes have them flattened
- **Caching**: No cache invalidation needed as queries already included STILL fields

## Impact
- ContentSeries projects now display STILL images as posters in main menus
- ContentSeries episodes now display STILL images as posters in episode lists
- Improved visual consistency and quality for animated content
- No breaking changes to existing functionality

## Testing Results
- ✅ All unit tests pass (344/344)
- ✅ 97% code coverage maintained
- ✅ Kodi logs show correct artwork setting
- ✅ User verification: STILL images now appear as posters

## Documentation
Created `/docs/artwork_mapping.md` documenting the complete mapping from Angel Studios images to Kodi artwork types, including priorities and fallbacks.

## Status: COMPLETED ✅
The artwork regression has been fully resolved. STILL images now properly display as posters in Kodi for all ContentSeries content.