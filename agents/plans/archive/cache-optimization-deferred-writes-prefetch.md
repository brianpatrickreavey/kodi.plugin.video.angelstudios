# Cache Optimization: Deferred Writes & Background Prefetch

**Objective:** Optimize menu performance by deferring episode cache writes and adding background prefetch for projects and episodes. Deferred writes move blocking cache operations after UI render, while prefetch populates caches post-render so subsequent menu navigations operate entirely from cache.

**Status:** Superseded - Major performance improvements achieved through infotags optimization (85-90% reduction in menu render time). Current caching performance deemed adequate.

**Decision:** Implementation no longer needed. Infotags direct access optimization achieved the performance goals this plan targeted. Reassess only if future performance data shows new bottlenecks.

**Design Decisions:**
- Use API response order for prefetch priority (no cross-navigation tracking)
- Allow prefetch to complete silently even if user navigates away (no cleanup needed)
- Defer only batch-fetched episodes (avoid redundant cache rewrites of cache-hit episodes)
- Log API errors and abandon prefetch silently (no retry)
- Prefetch all seasons' episodes together in seasons_menu (user could navigate to any season next)

---

## Implementation Steps

### Step 1: Move Episode Cache Writes to Deferred Phase
**File:** `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
**Method:** `episodes_menu()`
**Change:** Collect only batch-fetched episodes (from `missing_guids`), remove synchronous `_set_episode()` calls, defer writes to `_deferred_cache_write()` after `endOfDirectory()`.
**Impact:** Allows episode menu to render before cache writes execute, improving UI latency.

### Step 2: Implement `_deferred_prefetch_project()` Helper
**File:** `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
**Location:** After `_deferred_cache_write()` method
**Signature:** `_deferred_prefetch_project(self, project_slugs, max_count=None)`
**Logic:**
- Query SimpleCache for uncached project slugs using `_execute_sql()` with LIKE pattern `project_%`
- Extract uncached slugs from input list
- Limit to max_count if provided (read from settings)
- For each uncached slug, fetch via `angel_interface.get_project(slug)`, cache with TTL, log
- Abandon silently on API error (no retry)
**Impact:** Populates project cache in background after projects_menu renders.

### Step 3: Integrate Prefetch into `projects_menu()`
**File:** `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
**Method:** `projects_menu()`
**Change:** After `xbmcplugin.endOfDirectory(self.handle)`, call `_deferred_prefetch_project()` with project list and max count from settings.
**Impact:** Start background prefetch for top N uncached projects after menu displays.

### Step 4: Implement `_deferred_prefetch_episodes()` Helper
**File:** `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
**Location:** After `_deferred_prefetch_project()` method
**Signature:** `_deferred_prefetch_episodes(self, project)`
**Logic:**
- Extract all episode GUIDs from all seasons in project
- Query SimpleCache for uncached episodes using LIKE pattern `episode_%`
- Identify uncached GUIDs
- Batch-fetch missing GUIDs via `angel_interface.get_episodes_for_guids()`
- For each fetched episode, cache via `_set_episode()` with TTL
- Log results and errors, abandon silently on API error
**Impact:** Populates episode cache for all seasons in background after seasons_menu renders.

### Step 5: Integrate Prefetch into `seasons_menu()`
**File:** `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
**Method:** `seasons_menu()`
**Change:** After `xbmcplugin.endOfDirectory(self.handle)` (multi-season branch), call `_deferred_prefetch_episodes(project)`.
**Impact:** Start background prefetch for all seasons' episodes after menu displays.

### Step 6: Add Prefetch Settings
**File:** `plugin.video.angelstudios/resources/settings.xml`
**New Settings:**
- `enable_prefetch` (bool, default true): Enable/disable background prefetch
- `prefetch_project_count` (int, range 1-20, default 5): Max projects to prefetch per projects_menu render
**Usage:** Check settings in helper methods before executing prefetch; skip if disabled.

---

## Testing Strategy

- **Unit tests:** Mock SimpleCache, angel_interface, verify deferred writes collect only batch-fetched episodes
- **Integration tests:** Verify prefetch helpers query cache correctly, fetch missing data, handle errors gracefully
- **Timing tests:** Confirm deferred writes don't impact UI latency, prefetch completes silently
- **Caching tests:** Verify episode_menu makes zero network calls post-prefetch (all cache hits)

---

## Rollback Plan

- Revert deferred writes in episodes_menu: restore synchronous `_set_episode()` calls
- Remove prefetch helpers: delete `_deferred_prefetch_project()` and `_deferred_prefetch_episodes()`
- Remove prefetch calls: delete calls from projects_menu and seasons_menu
- Remove settings: delete prefetch entries from settings.xml
