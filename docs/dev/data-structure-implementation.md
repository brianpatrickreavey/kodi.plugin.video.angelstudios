# Data Structure - Implementation

## Overview
This document covers the implementation details, GraphQL requirements, future enhancements, and design rationale for the caching architecture.

## Decision
Use SimpleCache with custom TTLs; implement service addon for watch position sync.

## Rationale
- SimpleCache provides reliable key-value storage without complexity
- Service addon enables background sync without blocking UI
- Design balances performance, freshness, and simplicity

## Implementation Details

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

### Future Enhancements

#### Possible Optimizations

1. **Prefetching:** Cache next episode when user watches current episode
2. **Smart invalidation:** Invalidate specific episodes when API signals metadata changes
3. **Compression:** Serialize cache entries as compressed JSON if size becomes an issue

#### Migration Notes

**Cache Invalidation Required:** If migrating from pre-fat-query implementation, invalidate all `project_{slug}` caches to force refetch with new structure (full project with sparse episodes: id, guid, episodeNumber, __typename). Episode caches (`episode_{guid}`) should also be invalidated to ensure normalized field structure.

#### Not Recommended

1. **Caching in angel_interface:** Keep caching in UI layer to maintain API layer's KODI-agnostic design
2. **In-memory cache:** SimpleCache already uses window properties for memory caching; adding another layer adds complexity without benefit
3. **Episode-level nested navigation:** Episodes don't need season/project structure; reverse lookup via projectSlug is sufficient

### Design Rationale

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

## Constraints
- Assumes Angel API v1 schema stability
- Service addon requires careful lifecycle management
- Future enhancements depend on API capabilities

## Files
- `kodi_cache_manager.py`: Cache operations
- `angel_interface.py`: API calls and normalization
- `service.py`: Service addon entry
- `angel_playback_monitor.py`: Player monitoring
- GraphQL queries: Various query files

## For Agents/AI
Use SimpleCache for key-value storage; implement service for background sync; normalize API responses; design for cross-path reuse.