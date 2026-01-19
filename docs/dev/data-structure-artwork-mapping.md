# Artwork Mapping: Angel Studios to Kodi

## Overview
This document describes the mapping of Angel Studios image fields to Kodi artwork types in the plugin. The mapping prioritizes STILL images for ContentSeries content to provide consistent, high-quality artwork.

## Decision
Implemented a priority-based mapping system that favors STILL images over discovery posters for ContentSeries projects and episodes.

## Rationale
STILL images provide higher quality and consistency compared to dynamically generated discovery posters. This improves visual experience for series content while maintaining fallbacks for movies and edge cases.

## Kodi Artwork Types
- **poster**: Vertical image for thumbnails and posters
- **landscape/fanart**: Horizontal background image
- **logo/clearlogo/icon**: Branding elements (logo reused for all)
- **thumb**: Thumbnail (same as poster)

## Angel Studios Image Fields

### Project Images (from `query_getProjectsForMenu.graphql`)
- `discoveryPosterCloudinaryPath`: Vertical poster (fallback)
- `discoveryPosterLandscapeCloudinaryPath`: Horizontal poster (fallback)
- `logoCloudinaryPath`: Show logo
- `title.portraitTitleImage`: STILL vertical (highest priority)
- `title.landscapeTitleImage`: STILL horizontal (highest priority)
- Additional STILL images (not used for primary mapping)

### Episode Images (from `query_getProject.graphql`, merged)
- `portraitStill1/2/3`: STILL vertical (portraitStill1 priority)
- `landscapeStill1/2/3`: STILL horizontal (landscapeStill1 priority)
- Discovery paths as fallbacks

## Mapping Logic

### Poster (Vertical)
1. STILL image (`portraitTitleImage` or `portraitStill1`)
2. Fallback: `discoveryPosterCloudinaryPath`

### Landscape/Fanart (Horizontal)
1. STILL image (`landscapeStill1`)
2. Fallback: `discoveryPosterLandscapeCloudinaryPath`

### Logo/Clearlogo/Icon
- `logoCloudinaryPath` (reused for all three)

### Thumb
- Same as poster

## Implementation Details
- Handled in `kodi_menu_handler.py::_process_attributes_to_infotags()` (lines ~770–820)
- STILL images nested under `title` for projects; flattened for episodes
- Cloudinary URLs built once and reused (e.g., logo for multiple art keys)
- Fallbacks ensure availability even if STILL images fail

## Constraints
- Assumes Angel API v1 schema stability
- STILL images only available for ContentSeries; movies use discovery posters
- Manual updates needed for new image fields

## Files
- `kodi_menu_handler.py` (artwork processing in `_process_attributes_to_infotags()`)
- GraphQL queries: `query_getProjectsForMenu.graphql`, `query_getProject.graphql`

## Examples
- **ContentSeries Project**: Poster = `portraitTitleImage`, Landscape = `landscapeStill1`
- **Episode**: Poster = `portraitStill1`, Landscape = `landscapeStill1`
- **Movie**: Poster = `discoveryPosterCloudinaryPath`, Landscape = `discoveryPosterLandscapeCloudinaryPath`

## For Agents/AI
Artwork mapping is schema-dependent; prioritize STILL images for series. Update mappings if API adds new fields. Reuse URLs in code to avoid redundant `get_cloudinary_url()` calls.