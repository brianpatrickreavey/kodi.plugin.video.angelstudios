# Data Structure - Cache Strategy

## Overview
This document details the caching strategies, key patterns, write behaviors, and coherence mechanisms for the two-level cache system.

## Decision
Use separate TTLs and blind overwrites for fresh data; prioritize episode-level caching for reuse.

## Rationale
- Projects change frequently, so shorter TTL; episodes stable, longer TTL
- Blind overwrites ensure watch positions stay current
- Episode-level caching maximizes cross-path reuse

## Implementation Details

### Cache Key Patterns

| Cache Key | Content | Purpose | Size | TTL |
|-----------|---------|---------|------|-----|
| `project_{slug}` | Full project metadata + ultra-sparse episode stubs | Navigation index | ~5-10KB | User setting (default 8h) |
| `episode_{guid}` | Complete episode data from EpisodeListItem fragment | Display & playback | ~5KB | User setting (default 72h) |

Default TTL rationale:
- Projects change more frequently (new episodes, artwork tweaks), so cache shorter (8h)
- Episodes are stable once released; use longer TTL (72h) while still respecting manual clear/disable settings

### Cache Write Strategy

#### Fat ResumeWatching Path (Blind Overwrite)

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

#### Other Paths (Cache-First)

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

### Cache Coherence

#### Potential Duplication

Episode data can exist in two places:
1. **Nested in project cache:** `project_{slug}.seasons[].episodes[]` (sparse)
2. **Standalone episode cache:** `episode_{guid}` (full)

**This is intentional:**
- Project cache: Full project + seasons with sparse episodes for navigation
- Episode cache: Full episode data for display/playback
- Duplication is minimal (~150 bytes per episode in project vs 5KB in episode cache)

#### Authoritative Source Priority

When episode data exists in both caches:
- **For navigation:** Use sparse data from project cache (guid + episodeNumber)
- **For display/playback:** Use full data from episode cache (EpisodeListItem)
- **For watch position:** Fat resumeWatching blindly overwrites with fresh data; other paths use cached watchPosition

#### Staleness Handling

Caches use separate TTL settings:
- **Projects:** 8 hours (default) - change more frequently
- **Episodes:** 72 hours (default) - stable once released
- User can disable cache entirely in settings (applies to both)
- User can clear cache manually (clears both)
- Cache automatically expires after TTL
- Continue watching: API errors show error dialog (no stale cache fallback)
- Other paths: Can gracefully use stale cache on API failure

## Constraints
- Blind overwrites assume fat query data is authoritative
- Separate TTLs require careful tuning to balance freshness and performance
- Duplication is acceptable for minimal overhead

## Files
- `kodi_cache_manager.py`: Cache operations and TTL management
- `angel_interface.py`: Blind write logic for resume watching

## For Agents/AI
Use blind overwrites for fresh watch positions; cache episodes at guid level; set project TTL shorter than episodes; handle staleness with user settings.