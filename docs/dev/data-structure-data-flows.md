# Data Structure - Data Flows

## Overview
This document describes the three main data flows in the caching architecture: continue watching, series browsing, and episode playback.

## Decision
Use fat queries for fresh data in continue watching; cache-first approach elsewhere.

## Rationale
- Continue watching needs always-fresh watch positions, so fat query every time
- Other flows can reuse cached data for performance
- Episode-level caching enables cross-flow reuse

## Implementation Details

### 1. Continue Watching Menu (Fat ResumeWatching)

```
User opens Continue Watching
  ↓
1. Query fat resumeWatching(first: 10)
   Returns: Full episode data (with type-specific aliases) +
            Complete project data (with sparse episodes) for each unique project +
            {pageInfo}
  ↓
2. Normalize episodes:
   For each episode in response:
   ├─ Map type-specific aliases to canonical names (episodeSubtitle → subtitle)
   ├─ Flatten nested structures (season.seasonNumber → seasonNumber)
   ├─ Add guid from node.watchableGuid
   └─ Skip unknown content types
  ↓
3. Blind-write episodes to cache:
   For each normalized episode:
   └─ _set_episode(guid, episode_data)  # 72h TTL
  ↓
4. Blind-write projects to cache:
   For each unique project in response (full nested structure):
   └─ cache.set("project_{slug}", project_data, ttl=8h)
      Project includes: name, slug, projectType, seasons with sparse episodes
  ↓
5. Render menu directly from normalized data:
   ├─ Episode metadata (after normalization)
   └─ Project metadata from response
  ↓
6. On API failure:
   └─ Show error dialog + empty menu (no stale cache fallback)
```

**Optimization Impact:**
- **Every load:** 1 query (fat resumeWatching always called for fresh positions)
- **Response size:** ~60-70 KB for 10 items (full episodes with nested projects)
- **Cross-path benefit:** Episodes and projects cached for immediate reuse in series browsing and playback
- **Normalization overhead:** Negligible (~1ms per episode for alias mapping and flattening)

### 2. Series Browsing → Episodes Menu

```
User navigates: Series → "The Chosen" → Season 1
  ↓
1. Check cache.get("project_the-chosen")
   ├─ If HIT: Use cached project
   └─ If MISS: Query get_project(slug)
      Returns: Full nested structure
      Cache as project_{slug}
  ↓
2. Extract season.episodes[] (sparse data)
   episode_guids = [ep.guid for ep in season.episodes]
  ↓
3. For each guid:
   ├─ Check cache.get("episode_{guid}")
   ├─ If HIT: Use cached full episode
   └─ If MISS: Add to fetch_list[]
  ↓
4. If fetch_list not empty:
   └─ Batch query get_episodes_for_guids(fetch_list)
      Cache each as episode_{guid}
  ↓
5. Render episode menu using:
   ├─ Full episode data from episode_{guid} caches
   └─ Apply progress bars from episode.watchPosition
```

**Optimization Impact:**
- **First load:** 2 queries (project + batch episodes)
- **Second load:** No queries (all cached)
- **Cross-path benefit:** Episodes cached here available in continue watching

### 3. Episode Playback

```
User plays episode (from any menu)
  ↓
1. Check cache.get("episode_{guid}")
   ├─ If HIT:
   │  ├─ Extract source.url
   │  └─ Play immediately (no project fetch needed!)
   │
   └─ If MISS:
      ├─ Check cache.get("project_{slug}")
      │  └─ If HIT: Find episode in nested seasons.episodes
      │
      └─ If MISS: Query get_project(slug)
         └─ Cache as project_{slug}
         └─ Find episode in nested structure
         └─ Cache as episode_{guid} for future reuse
  ↓
2. Play video using source.url
   └─ InputStream Adaptive configured per user settings
```

**Optimization Impact:**
- **From cached episode:** Zero queries, instant playback
- **Fallback:** One project query (same as current behavior)

## Constraints
- Fat query in continue watching ensures freshness but increases load
- Cache-first in other flows assumes data stability
- Batch fetching reduces API calls but requires guid extraction

## Files
- `kodi_menu_handler.py`: Menu rendering logic
- `angel_interface.py`: API calls and normalization
- `kodi_cache_manager.py`: Cache checks and writes

## For Agents/AI
Fat query for continue watching; cache-first for browsing/playback; normalize responses; batch fetch missing episodes.