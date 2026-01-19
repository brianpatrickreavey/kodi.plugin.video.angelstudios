# Angel Data Retrieval and Caching Refactor Plan

## Plan: Two-Level Episode/Project Cache with Fat ResumeWatching

Refactor caching to support episode-level cache reuse across navigation paths, powered by an enriched resumeWatching query that returns full episode and project data, eliminating follow-up fetches on the continue watching path.

### Steps

1. **Update data_structure.md** to reflect fat resumeWatching design: continue watching flow now receives full EpisodeListItem + complete project structure (all artwork/trailers/ratings/etc. with sparse episodes) in one query, blindly overwrites `episode_{guid}` and `project_{slug}` caches, renders directly without merge logic; resumeWatching failure shows error + empty menu (no stale fallback); update optimization impact (first load: 1 query instead of 3).

2. **Extend query_resumeWatching.graphql** to include EpisodeListItem fragment for each episode and full project fields (matching getProject structure minus fat episodes) for each unique project; ensure response structure allows extracting episodes and projects for caching.

3. **Add episode cache helpers to kodi_ui_interface.py**: `_get_episode(guid)` reads `episode_{guid}` cache, `_set_episode(guid, data, ttl)` writes with configurable TTL; add `_episode_cache_ttl()` returning 72h default (separate from project TTL).

4. **Refactor kodi_ui_interface.py**: call fat resumeWatching, extract episodes and projects from response, blindly write to `episode_{guid}` (72h TTL) and `project_{slug}` (8h TTL) caches, render menu directly from response data; on API failure, show error dialog and empty menu.

5. **Refactor kodi_ui_interface.py**: extract episode guids from `project_{slug}.seasons[].episodes[]` (sparse), check `episode_{guid}` cache for each, batch-fetch misses via `get_episodes_for_guids`, cache misses with 72h TTL, render from cached episodes.

6. **Refactor kodi_ui_interface.py**: prefer `episode_{guid}` cache (instant playback if hit), fallback to `project_{slug}` cache (find episode in nested structure), final fallback to `get_project` network call; write fetched episode to `episode_{guid}` cache for future reuse.

7. **Add settings in resources/settings.xml**: replace single `cache_expiration_hours` slider with two sliders: `project_cache_hours` (default 8) and `episode_cache_hours` (default 72) under Advanced group; ensure `disable_cache` and clear cache button apply to both.

8. **Update cache clear/disable logic**: ensure `clear_cache()` and `_cache_enabled()` in kodi_ui_interface.py apply uniformly to both `project_{slug}` and `episode_{guid}` cache keys.

9. **Add/update tests**: fat resumeWatching response parsing, episode cache read/write with 72h TTL, project cache with 8h TTL, continue watching renders from response without follow-up calls, series browsing reuses episode cache, playback prefers episode cache, cache disable/clear affects both caches, resumeWatching failure shows error.

### Further Considerations

1. **GraphQL response size validation**: After implementing fat resumeWatching, log actual response sizes for 10-item pages to confirm ~60-70 KB estimate and identify any payload bloat.

2. **Sparse episode field selection**: Which fields from getProject's nested episodes should be included in `project_{slug}.seasons[].episodes[]`? Currently assuming guid/episodeNumber/seasonNumber/name/subtitle—confirm if additional fields (e.g., availability status) are needed for menu rendering.

3. **Error handling for partial failures**: If fat resumeWatching returns some episodes but not others (partial data), should we render what we have or treat it as full failure?

4. **Migration path for existing caches**: Should we invalidate old `project_{slug}` caches (which have full episodes) when deploying new sparse structure, or handle both formats gracefully?

5. **Batch project fetching strategy**: Step 4 mentions writing projects from fat resumeWatching response—do we need a batch project query for cases where multiple unique projects appear in continue watching but aren't in the response, or does fat resumeWatching always embed all needed projects?

---

## Decisions & Considerations (Tracking)

- **Cache Architecture (Decided):** Two-level caches.
  - `project_{slug}`: full project metadata + sparse episodes (only `id`, `guid`, `episodeNumber`), TTL ~8h, used for navigation.
  - `episode_{guid}`: full EpisodeListItem for playback/display, TTL ~72h.
- **ResumeWatching (Decided):** Use fat resumeWatching; always query for fresh positions; blind-write episodes/projects to cache from response.
- **Failure Handling (Decided):** If resumeWatching fails, show error and render empty menu (no stale fallback of continue-watching list).
- **Project Embedding (Decided):** Fat resumeWatching embeds complete project payload (with sparse episodes) for all unique projects in response. Projects do not support paginated `seasons(first:N)` edges format; use simple list format.
- **Cache Migration (Decided):** Invalidate existing `project_{slug}` caches when deploying sparse episode stubs format.
- **Menu Rendering (Decided):** Episodes menu reads GUIDs from project sparse stubs; hydrates full episodes from cache; batch-fetches misses.
- **Playback Fallbacks (Decided):** Episode cache → project cache → network; write episodes to cache on misses.
- **URL Extraction (Decided):** Fat query returns `url` at episode top level; code must check both `source.url` (batch queries) and `episode.url` (fat query) for availability and playback.

### Work Completed (January 9-10, 2026)

✅ **Fixed unavailable episode crash** - Added None-value sanitization in `_create_list_item_from_episode` before metadata processing (line ~1247 in kodi_ui_interface.py).

✅ **Implemented fat resumeWatching query** - Replaced broken EpisodeListItem fragment with schema-aligned query using type-specific aliases (episodeSubtitle, episodeImage, episodeDescription, etc.). Returns full episodes at top level + complete projects with sparse episodes (id, guid, episodeNumber).

✅ **Added episode normalizer helper** - `_normalize_resume_episode(content, node)` in angel_interface.py maps type-specific aliases to canonical fields, flattens season.seasonNumber, adds guid from watchableGuid, maps watch position.

✅ **Fixed availability detection** - Updated `_create_list_item_from_episode` to check both `episode.get("source")` and `episode.get("url")` (line ~1228).

✅ **Fixed stream URL extraction** - Updated `play_episode` to check for URL at both `source.url` and top-level `url` (line ~851).

✅ **Fixed cast handling** - Extract actor dicts from list, create xbmc.Actor objects with error handling (lines ~1329-1338).

✅ **Re-enabled project caching** - Projects from fat query now have full seasons structure; safe to cache and reuse in seasons_menu.

✅ **Continue watching feature working end-to-end** - Renders items correctly, plays episodes without errors, shows watch progress bars.

### Open Items / To Do (January 10-11, 2026)

**Today's Completed Tasks (January 10, 2026):**

✅ **Test suite rectified - 100% coverage achieved**
- Fixed 2 failing tests from fat query implementation
- Added comprehensive edge case coverage tests
- **Final Results: 312/312 tests passing, 100% coverage (1484/1484 lines)**

**Tomorrow's Tasks:**

1. **Audit caching in episodes_menu** - Profile episodes_menu to identify slow paths and excessive data churning. Confirm episode cache is being hit and misses are being batched correctly. Optimize any unnecessary queries.

2. **Refactor GraphQL queries to share fragments** - Review current fragments and query definitions; consolidate episode field selection into reusable fragments. Likely candidates:
   - Create unified fragment for sparse episodes (id, guid, episodeNumber)
   - Consolidate type-specific aliases handling if schema allows

3. **Cleanup and polish** -
   - Remove any debug logging added during troubleshooting
   - Update docstrings if behavior has changed
   - Confirm cache TTL defaults in settings match plan (8h projects, 72h episodes)
   - Validate no orphaned code or dead branches

4. **Documentation updates** - Confirm data_structure.md accurately reflects final implementation (already updated during work, but verify schema details and sparse episode fields).

### Remaining Backlog (Lower Priority)

- Batch project fetching for series beyond first 20 seasons (currently limits to `first:20` in fat query)
- Prefetching strategy for next episode when user watches current
- Smart invalidation signals from API if metadata changes
- Response size metrics collection and reporting
