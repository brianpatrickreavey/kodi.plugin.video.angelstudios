# Data Structure - Episode Formats

## Overview
This document explains the difference between sparse and full episode data formats, and the normalization process for API responses.

## Decision
Use sparse episodes in project cache for navigation; full episodes for display/playback; normalize type-specific aliases.

## Rationale
- Sparse format minimizes cache size for navigation
- Full format provides all needed metadata for playback
- Normalization ensures consistent field names across content types

## Implementation Details

### Sparse Episode (in project_{slug} cache)

Minimal fields needed for navigation and ordering:

```json
{
  "id": "episode-id-123",
  "guid": "episode-guid-123",
  "episodeNumber": 1,
  "__typename": "ContentEpisode"
}
```

**Size:** ~150 bytes per episode
**Purpose:** Extract guids for batch fetch, maintain episode ordering in season

### Full Episode (in episode_{guid} cache)

Complete data from fat resumeWatching query (after normalization):

```json
{
  "__typename": "ContentEpisode",
  "id": "...",
  "guid": "episode-guid-123",
  "slug": "...",
  "episodeNumber": 1,
  "seasonNumber": 1,
  "name": "Episode 1",
  "subtitle": "I Have Called You By Name",
  "description": "Long description...",
  "image": {
    "cloudinaryPath": "...",
    "__typename": "Image"
  },
  "posterCloudinaryPath": "...",
  "posterLandscapeCloudinaryPath": "...",
  "releaseDate": "...",
  "duration": 3600,
  "url": "https://stream.angelstudios.com/...",
  "watchPosition": {
    "position": 1234
  },
  "season": {
    "id": "...",
    "seasonNumber": 1,
    "__typename": "Season"
  },
  "project": {
    "id": "...",
    "name": "The Chosen",
    "slug": "the-chosen",
    "projectType": "SERIES",
    "seasons": [...],
    "__typename": "Project"
  },
  "genres": ["Drama", "Faith"],
  "cast": [{"name": "...", "__typename": "Actor"}],
  "watchableAvailabilityStatus": "AVAILABLE",
  "watchableAt": null,
  "actionsToWatch": [],
  "introStartTime": 10,
  "introEndTime": 60
}
```

**Size:** ~5KB per episode
**Purpose:** Display metadata, playback, progress tracking

**Type-Specific Aliases:** The fat query returns episodes with type-specific field aliases that get normalized:
- `ContentEpisode`: `episodeSubtitle` → `subtitle`, `episodeImage` → `image`, `episodeDescription` → `description`
- `ContentSpecial`: `specialSubtitle` → `subtitle`, `specialImage` → `image`, `specialDescription` → `description`
- `ContentMovie`: `movieSubtitle` → `subtitle`, `movieImage` → `image`, `movieDescription` → `description`

Normalization also flattens `season.seasonNumber` to top-level `seasonNumber` and adds `guid` from `node.watchableGuid`.

## Constraints
- Sparse format assumes guids are sufficient for fetching full data
- Normalization requires mapping all type variants
- Full format includes nested structures that may need flattening

## Files
- `angel_interface.py`: Normalization logic in `_normalize_resume_episode()`
- GraphQL queries: `query_resumeWatching.graphql` for type-specific aliases

## For Agents/AI
Normalize type-specific aliases to canonical names; use sparse for navigation, full for playback; flatten nested season data.