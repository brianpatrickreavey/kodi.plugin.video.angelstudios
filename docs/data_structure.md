# Data Structure & Caching Architecture

## Overview

This document describes the two-level caching architecture used to optimize data fetching and enable cross-path cache reuse between different navigation flows (continue watching, series browsing, playback).

## Core Principles

1. **Episode data should be fetched once and reused everywhere** - An episode cached from continue watching should be available when browsing that series, and vice versa
2. **Project cache serves as navigation index** - Projects contain sparse episode metadata needed for menu rendering
3. **Episode cache contains complete playback data** - Full metadata including source URLs, artwork, watch position
4. **Watch positions are always fresh** - Fat resumeWatching returns complete fresh data and blindly overwrites cache

## Cache Structure

### Two-Level Cache System

```
┌─────────────────────────────────────────────────────────────┐
│                     SimpleCache (Kodi)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Project Index Cache (Navigation)                           │
│  ├─ project_{slug}                                          │
│  │  ├─ name, slug, projectType (full metadata)             │
│  │  └─ seasons[]                                            │
│  │     ├─ id, name, seasonNumber                           │
│  │     └─ episodes[] (SPARSE - navigation only)            │
│  │        ├─ id, guid, episodeNumber, __typename           │
│  │        └─ (5 fields for ordering/batch fetch)           │
│  │                                                          │
│  Episode Detail Cache (Playback & Display)                  │
│  └─ episode_{guid}                                          │
│     ├─ All fields from EpisodeListItem fragment            │
│     ├─ source {url, duration, credits}                     │
│     ├─ watchPosition {position} (merged from API)          │
│     ├─ artwork, metadata, availability                     │
│     └─ projectSlug (for reverse lookup)                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Cache Key Patterns

| Cache Key | Content | Purpose | Size | TTL |
|-----------|---------|---------|------|-----|
| `project_{slug}` | Full project metadata + ultra-sparse episode stubs | Navigation index | ~5-10KB | User setting (default 8h) |
| `episode_{guid}` | Complete episode data from EpisodeListItem fragment | Display & playback | ~5KB | User setting (default 72h) |

Default TTL rationale:
- Projects change more frequently (new episodes, artwork tweaks), so cache shorter (8h)
- Episodes are stable once released; use longer TTL (72h) while still respecting manual clear/disable settings

## ContentSeries Integration (STILL Images)

### Dual-Source Episode Data

Starting with version implementing episode artwork improvements, episodes are fetched from **two API paths** and merged:

1. **ContentSeries path** (`project.title.ContentSeries.seasons.episodes`):
   - Display metadata: `name`, `subtitle`, `description`
   - STILL images: `portraitStill1-5`, `landscapeStill1-5`
   - Aspect ratios: `2:3` (portrait), `16:9` (landscape)
   - Categories: `STILL_1` through `STILL_5`
   - **Limitation**: NO playback fields (source, watchPosition, upNext, intro markers)

2. **Episode path** (`project.seasons.episodes` or `episode(guid)`):
   - Playback fields: `source.url`, `watchPosition`, `upNext`, `introStartTime/EndTime`, `vmapUrl`
   - Display fields: `name`, `subtitle`, `description`, `posterCloudinaryPath`
   - **Limitation**: Cannot query `image()` field (parsing error)

### Relay Pagination Unwrapping

ContentSeries uses Relay pagination pattern with `edges`/`node` nesting:

```graphql
seasons {
  edges {
    node {
      episodes {
        edges {
          node {
            # Episode fields here
          }
        }
      }
    }
  }
}
```

Helper function `_unwrap_relay_pagination()` flattens this structure to plain lists.

### Episode Cache Structure with STILLs

```json
{
  "episode_{guid}": {
    // Display fields (from ContentSeries - preferred)
    "name": "Episode Title",
    "subtitle": "Episode Subtitle",
    "description": "Full description text",

    // STILL images (from ContentSeries - 2:3 aspect)
    "portraitStill1": {"cloudinaryPath": "v1234/path1.jpg"},
    "portraitStill2": {"cloudinaryPath": "v1234/path2.jpg"},
    "portraitStill3": {"cloudinaryPath": "v1234/path3.jpg"},
    "portraitStill4": {"cloudinaryPath": "v1234/path4.jpg"},
    "portraitStill5": {"cloudinaryPath": "v1234/path5.jpg"},

    // STILL images (from ContentSeries - 16:9 aspect)
    "landscapeStill1": {"cloudinaryPath": "v1234/land1.jpg"},
    "landscapeStill2": {"cloudinaryPath": "v1234/land2.jpg"},
    "landscapeStill3": {"cloudinaryPath": "v1234/land3.jpg"},
    "landscapeStill4": {"cloudinaryPath": "v1234/land4.jpg"},
    "landscapeStill5": {"cloudinaryPath": "v1234/land5.jpg"},

    // Playback fields (from Episode path)
    "source": {
      "url": "https://stream.angelstudios.com/...",
      "duration": 3600,
      "credits": 3480
    },
    "watchPosition": {"position": 1234},
    "upNext": {...},
    "introStartTime": 10,
    "introEndTime": 60,
    "vmapUrl": "..."
  }
}
```

**Cache size impact**: Episodes grow from ~5KB to ~7-8KB with STILL fields (acceptable overhead).

### Artwork Priority Changes

**Poster (portrait) priority**:
1. `portraitStill1` - Primary episode still
2. `portraitStill2-5` - Additional episode stills
3. `title.portraitTitleImage` - Project title art (existing)
4. `discoveryPoster` - Fallback (existing)
5. `posterCloudinaryPath` - Legacy fallback (may be landscape)

**Fanart (landscape) mapping**:
- `landscapeStill1-5` → `fanart`, `fanart1-4` (episode context)
- `title.landscapeAngelImage1-3` → additional fanart slots (project context)
- `discoveryPosterLandscape` → fallback

This fixes the original issue: some episodes showed landscape thumbnails in `posterCloudinaryPath`, causing inconsistent aspect ratios. STILLs ensure proper portrait images.

### Unreleased Episodes

Episodes without released video return `null` for all STILL fields. Artwork logic handles this gracefully by falling through to next priority source.

### Resume Watching Limitation

Episodes in Resume Watching menu do NOT have STILL images. The `fat resumeWatching` query uses Episode type directly, not ContentSeries path. They fall back to `posterCloudinaryPath`. This is acceptable as the primary browse path (Projects → Seasons → Episodes) has full STILL support.

### Service Addon + PlayerMonitor

To support future watch position API sync, a Service extension runs continuously:

**Architecture**:
- **Service entry**: `resources/lib/service.py` - Continuous loop with xbmc.Monitor
- **Player monitor**: `resources/lib/angel_playback_monitor.py` - Extends xbmc.Player, catches callbacks
- **Communication**: WindowProperties (`xbmcgui.Window(10000)`) bridge plugin ↔ service contexts

**Lifecycle**:
1. Kodi starts → Service initializes AngelPlaybackMonitor
2. Plugin sets `angelstudios.playing_guid` property before playback
3. Service's onPlayBackStarted() reads GUID from property
4. Playback happens (plugin exits after setResolvedUrl)
5. Service's onPlayBackEnded/Stopped() triggers cache refresh
6. Future Phase 2: Service writes watchPosition to API

**Current behavior**: Service fetches fresh episode data after playback ends (includes updated watchPosition), but does NOT yet write to cache (TODO).

**Future Phase 2**: Service will call `_update_watch_position_to_api()` to sync watch position server-side across devices.

## Data Flows

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

## Sparse vs Full Episode Data

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

## Cache Write Strategy

### Fat ResumeWatching Path (Blind Overwrite)

Continue watching always calls fat resumeWatching for fresh data and blindly overwrites cache:

```python
# 1. Get fresh data from fat resumeWatching (normalization happens in angel_interface)
response = angel_interface.get_resume_watching(first=10)

# 2. Blind-write episodes (no merge needed - data is fresh and normalized)
for episode in response['episodes']:
    episode_guid = episode.get('guid')
    if episode_guid:
        self._set_episode(episode_guid, episode)  # Uses 72h TTL from settings

# 3. Blind-write projects (no merge needed - data is fresh)
for project_slug, project_data in response['projects'].items():
    cache_key = f"project_{project_slug}"
    if self._cache_enabled():
        self.cache.set(cache_key, project_data, expiration=self._project_cache_ttl())  # 8h default
```

**Rationale:** Fat resumeWatching returns complete fresh data; no need to read/merge/write - just overwrite.

### Other Paths (Cache-First)

Series browsing and playback check cache first, fetch on miss, write new data:

```python
# Check cache
cached = cache.get(f"episode_{guid}")
if cached:
    return cached

# Fetch on miss
episode = angel_interface.get_episodes_for_guids([guid])[guid]
cache.set(f"episode_{guid}", episode, expiration=timedelta(hours=72))
return episode
```

## Cache Coherence

### Potential Duplication

Episode data can exist in two places:
1. **Nested in project cache:** `project_{slug}.seasons[].episodes[]` (sparse)
2. **Standalone episode cache:** `episode_{guid}` (full)

**This is intentional:**
- Project cache: Full project + seasons with sparse episodes for navigation
- Episode cache: Full episode data for display/playback
- Duplication is minimal (~150 bytes per episode in project vs 5KB in episode cache)

### Authoritative Source Priority

When episode data exists in both caches:
- **For navigation:** Use sparse data from project cache (guid + episodeNumber)
- **For display/playback:** Use full data from episode cache (EpisodeListItem)
- **For watch position:** Fat resumeWatching blindly overwrites with fresh data; other paths use cached watchPosition

### Staleness Handling

Caches use separate TTL settings:
- **Projects:** 8 hours (default) - change more frequently
- **Episodes:** 72 hours (default) - stable once released
- User can disable cache entirely in settings (applies to both)
- User can clear cache manually (clears both)
- Cache automatically expires after TTL
- Continue watching: API errors show error dialog (no stale fallback)
- Other paths: Can gracefully use stale cache on API failure

## Implementation Notes

### SimpleCache Characteristics

- **Storage:** SQLite database + Kodi window properties
- **Thread safety:** Not needed (Kodi addons are single-threaded)
- **Query capability:** None (key-value only)
- **Atomic operations:** No merge support (must read-modify-write)
- **Size limits:** Reasonable for our use case (~10KB per project, ~5KB per episode)

### GraphQL Query Requirements

To support this architecture, GraphQL queries must:

1. **resumeWatching (FAT):** Return full episode data with type-specific aliases (episodeSubtitle, episodeImage, episodeDescription) + complete project data (full seasons with sparse episodes) for each unique project. Normalization happens in `_normalize_resume_episode()` to map aliases to canonical names.
2. **get_episodes_for_guids:** Use EpisodeListItem fragment (full episode data) for batch fetching on other paths
3. **get_project:** Return full project structure with sparse episodes (id, guid, episodeNumber, __typename)
4. **get_projects_by_slugs:** Deprecated - no longer needed with fat resumeWatching

## Future Enhancements

### Possible Optimizations

1. **Prefetching:** Cache next episode when user watches current episode
2. **Smart invalidation:** Invalidate specific episodes when API signals metadata changes
3. **Compression:** Serialize cache entries as compressed JSON if size becomes an issue

### Migration Notes

**Cache Invalidation Required:** If migrating from pre-fat-query implementation, invalidate all `project_{slug}` caches to force refetch with new structure (full project with sparse episodes: id, guid, episodeNumber, __typename). Episode caches (`episode_{guid}`) should also be invalidated to ensure normalized field structure.

### Not Recommended

1. **Caching in angel_interface:** Keep caching in UI layer to maintain API layer's KODI-agnostic design
2. **In-memory cache:** SimpleCache already uses window properties for memory caching; adding another layer adds complexity without benefit
3. **Episode-level nested navigation:** Episodes don't need season/project structure; reverse lookup via projectSlug is sufficient

## Design Rationale

This two-level cache system balances several competing concerns:

- **Performance:** Minimize API calls through aggressive caching
- **Freshness:** Always use latest watch positions from API
- **Reusability:** Cache at episode level for cross-path reuse
- **Navigation:** Cache project structure for menu rendering
- **Size:** Keep project cache sparse to minimize duplication
- **Simplicity:** Use SimpleCache as-is without custom query layer
- **KODI-agnostic API:** Keep angel_interface clean and testable

The result is a system where:
- First load of any feature requires API calls (unavoidable)
- Subsequent loads are fast (cached)
- Navigation between features reuses cached data (efficient)
- Watch positions are always current (accurate)
