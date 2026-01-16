# Artwork Mapping: Angel Studios to Kodi

## Overview
This document describes how Angel Studios image fields are mapped to Kodi artwork types in the plugin. The mapping prioritizes STILL images for ContentSeries content to provide consistent, high-quality artwork.

## Kodi Artwork Types
- **poster**: Vertical image used for movie/TV show thumbnails and posters
- **landscape/fanart**: Horizontal background image used for episode backgrounds and fanart
- **logo/clearlogo**: Show logo for branding
- **icon**: Small icon for menus and lists
- **thumb**: Thumbnail image, typically the same as poster

## Angel Studios Image Fields

### Project Images (from `query_getProjectsForMenu.graphql`)
- `discoveryPosterCloudinaryPath`: Main vertical poster (used as fallback)
- `discoveryPosterLandscapeCloudinaryPath`: Horizontal poster (used as fallback for landscape/fanart)
- `logoCloudinaryPath`: Show logo
- `title.portraitTitleImage`: STILL vertical image (highest priority for poster)
- `title.portraitAngelImage`, `title.portraitAngelImage2`, `title.portraitAngelImage3`: Additional vertical STILL images (not used for poster)
- `title.landscapeTitleImage`: STILL horizontal image (highest priority for landscape)
- `title.landscapeAngelImage`, `title.landscapeAngelImage2`, `title.landscapeAngelImage3`: Additional horizontal STILL images

### Episode Images (from `query_getProject.graphql`, merged into episodes)
- `portraitStill1`, `portraitStill2`, `portraitStill3`: STILL vertical images (portraitStill1 has highest priority for poster)
- `landscapeStill1`, `landscapeStill2`, `landscapeStill3`: STILL horizontal images (landscapeStill1 has highest priority for landscape)
- `discoveryPosterCloudinaryPath`: Fallback vertical poster
- `discoveryPosterLandscapeCloudinaryPath`: Fallback horizontal poster

## Mapping Logic

### Poster (Vertical Image)
**Priority Order:**
1. **Projects**: `title.portraitTitleImage` (STILL image)
2. **Episodes**: `portraitStill1` (STILL image)
3. **Fallback**: `discoveryPosterCloudinaryPath` (discovery poster)

### Landscape/Fanart (Horizontal Image)
**Priority Order:**
1. `landscapeStill1` (STILL image, if available)
2. **Fallback**: `discoveryPosterLandscapeCloudinaryPath` (discovery landscape)

### Logo/Clearlogo/Icon
- `logoCloudinaryPath` (used for all three Kodi types)

### Thumb
- Same as poster (STILL image or fallback)

## Implementation Notes
- STILL images are fetched from GraphQL queries and prioritized for ContentSeries content
- For non-ContentSeries content, only discovery images are used
- The mapping is handled in `kodi_ui_interface.py::_process_attributes_to_infotags()`
- STILL images are nested under `title` for projects, but flattened to top-level for episodes after merging
- Fallbacks ensure artwork is always available, even if STILL images fail to load

## Examples
- **Tuttle Twins (ContentSeries project)**: Poster uses `portraitTitleImage`, landscape uses `landscapeStill1` or discovery landscape
- **Tuttle Twins Episode**: Poster uses `portraitStill1`, landscape uses `landscapeStill1`
- **Regular Movie**: Poster uses `discoveryPosterCloudinaryPath`, landscape uses `discoveryPosterLandscapeCloudinaryPath`