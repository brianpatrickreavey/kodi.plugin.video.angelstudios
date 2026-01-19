# Menu Optimization Plan

**Status**: Partially implemented - Core optimizations completed (infotags direct access, debug logging), timing instrumentation added. Offscreen mode and comprehensive measurement still pending.
**Created**: 2026-01-10
**Last Updated**: 2026-01-19
**Target**: Kodi 20+ (xbmcaddon API 3.0.1+)

## Overview

This document outlines a **measurement-first approach** to menu performance optimization. Initial API research revealed that some proposed optimizations (setInfo batching, ListItem caching) have fundamental architectural constraints in Kodi 20+. We now focus on:
1. ✅ **Instrumentation & measurement** implemented in infotags processing
2. ❌ **Offscreen mode** for directory items (recommended but not implemented)
3. ✅ **Data-driven optimization** - major performance gains achieved through infotags optimization

**Key Finding**: Real bottlenecks were infotags processing overhead (85-90% reduction achieved) and debug logging (zero-overhead category system implemented). API latency remains the dominant factor in normal workflows.

## ✅ Implemented Optimizations

### 1. Infotags Direct Access Optimization
**Status**: ✅ **COMPLETED** - Archived as `optimize-infotags-direct-access.md`
- **Impact**: 85-90% reduction in episode processing time (33ms → 3-5ms)
- **Method**: Replaced generic dict iteration with direct attribute access
- **Files**: `menu_utils.py`, `kodi_menu_handler.py`

### 2. Category-Based Debug Logging
**Status**: ✅ **COMPLETED** - Archived as `category-based-debug-logging.md`
- **Impact**: Zero performance overhead for disabled debug categories
- **Method**: Selective promotion of debug logs to INFO level via user toggles
- **Files**: `kodi_utils.py`, `main.py`, settings.xml, strings.po

### 3. Timing Instrumentation
**Status**: ✅ **PARTIALLY IMPLEMENTED** - Added to infotags processing
- **Impact**: Performance measurement capability in hot paths
- **Method**: `time.perf_counter()` timing around critical operations
- **Files**: `menu_utils.py`, `kodi_menu_handler.py`

## ❌ Pending Optimizations

### Offscreen Mode for Directory Items
**Status**: ❌ **NOT IMPLEMENTED** - Still recommended for modest GUI lock savings
- **Current State**: Only used for playback items (`offscreen=is_playback`)
- **Recommendation**: Add `offscreen=True` to all directory ListItem constructors

### The Measurement Philosophy
Before optimizing, we must measure. Initial assumptions about UI bottlenecks were tested against Kodi's actual APIs and codebase. Several optimizations that appeared promising turned out to be architecturally unfeasible or impactful. We now instrument real menu operations to identify where time is actually spent.

### Key Findings from API Research
- **API latency dominates**: Typical API calls take 500–2000ms; ListItem creation takes 10–50ms
- **`setInfo()` provides no perf benefit**: Deprecated in Kodi 20+, internally loops through same setters as individual calls
- **ListItem caching is impossible**: C++ backing prevents serialization; ListItems are consumed on `addDirectoryItem()` and cannot be reused
- **Recipe caching (limited gain)**: Theoretical ~20-35% gain from caching metadata dicts is small relative to API latency dominance

### Recommended Path Forward
1. **Implement instrumentation** (time.perf_counter() around fetch, render, metadata application)
2. **Measure real menus** (continue watching, projects, seasons, episodes)
3. **Analyze bottlenecks** (API vs. GUI rendering vs. metadata vs. cache)
4. **Implement offscreen=True** (safe, modest benefit, easy to verify)
5. **Plan further optimizations** based on measurement data

## Recommended: Offscreen Mode for Directory Items

**Status**: Safe to implement now; recommended for modest GUI lock savings.

### Why This Works
- **Proven**: Already in use for playback items in `play_video()`
- **Safe**: No post-addDirectoryItem mutations in this addon; items are added and immediately consumed
- **Benefit**: Avoids 1–2 GUI lock acquisitions per item (~0.2–0.5ms per item on loaded systems)
- **Easy**: Single parameter change in ListItem constructors across all directory menus
- **Kodi 20+ only**: Already addon requirement (xbmcaddon 3.0.1)

### Implementation Sites
- [kodi_ui_interface.py:464](kodi_ui_interface.py#L464) `main_menu`: ListItem for each menu entry
- [kodi_ui_interface.py:581](kodi_ui_interface.py#L581) `continue_watching_menu`: episode list items via `_create_list_item_from_episode`
- [kodi_ui_interface.py:672](kodi_ui_interface.py#L672) `projects_menu`: project list items
- [kodi_ui_interface.py:709](kodi_ui_interface.py#L709) `seasons_menu`: season list items
- [kodi_ui_interface.py:752](kodi_ui_interface.py#L752) `episodes_menu`: episode list items
- [kodi_ui_interface.py:1142](kodi_ui_interface.py#L1142) `_create_list_item_from_episode`: helper used by multiple menus

### Expected Gain
- Per-item: ~0.2–0.5ms GUI lock savings (system-dependent)
- 50-item menu: ~10–25ms saved (modest but measurable)
- **Real value**: More noticeable on heavily loaded systems; transparent on fast systems

## Instrumentation & Measurement Plan

**Goal**: Add timing instrumentation to identify real bottlenecks before further optimization.

### Timing Points
Wrap key sections with `time.perf_counter()` in the following methods:

**Menu Methods** (`continue_watching_menu`, `projects_menu`, `seasons_menu`, `episodes_menu`):
1. Entry point (log method name + params)
2. Data fetch block (API call + cache operations)
3. Per-item rendering loop (ListItem creation + metadata + art)
4. Exit (log total time + item count; compute per-item average)

**Helper Methods**:
- `_process_attributes_to_infotags()`: Measure metadata setter overhead per call
- `_create_list_item_from_episode()`: Measure ListItem creation time per call
- Cache writes (after data fetch; measure write time)

### Log Format
```
[INFO] continue_watching_menu: Start (cache enabled)
[DEBUG] Fetched 10 items in 1023ms (API call: 950ms, cache write: 73ms)
[DEBUG] Item 1: ListItem + metadata in 12ms
[DEBUG] Item 2: ListItem + metadata in 11ms
...
[INFO] continue_watching_menu: Completed in 1287ms (10 items, 128.7ms/item)
```

### Expected Output
After measuring several menus, we'll have data showing:
- Actual API latency (dominant factor?)
- Actual ListItem creation time
- Actual metadata application overhead
- Cache hit/miss patterns
- Per-item averages for extrapolation

### Success Criteria
This instrumentation answers: "Where does time actually go?" Once measured, we optimize the real bottleneck(s).

## Discarded Optimization Ideas

The following optimizations were thoroughly researched and rejected due to architectural constraints or minimal expected gains. Documented here to avoid revisiting.

### Optimization #1: Batch Metadata via setInfo (DISCARDED)

**Why Discarded**: `setInfo()` is deprecated in Kodi 20+ and provides **zero performance benefit**.

**Technical Details**:
- `setInfo()` is not a true batching mechanism; it internally loops through the same individual setters we already call
- Kodi source code shows `setInfo()` → iterates metadata dict → calls individual VideoInfoTag setters for each key
- Net effect: **identical performance to current individual setter calls**
- Switching to `setInfo()` would add dict construction overhead with no upside

**Original Assumption**: Batch setter calls would reduce Python→C++ boundary crossings. Reality: There are still N boundary crossings regardless of whether we call N setters individually or loop through them in `setInfo()`.

**Decision**: Do not pursue. Not worth refactoring for zero gains.

---

### Optimization #2: ListItem Caching (DISCARDED)

**Why Discarded**: ListItems **cannot be cached** due to C++ architecture and consumption model.

**Technical Details**:
- ListItems are C++ objects with Python bindings; they are not serializable or copyable
- Once added to Kodi's directory via `addDirectoryItem()`, the ListItem is **consumed**; its internal state becomes tied to the directory control
- Attempts to reuse or serialize ListItems across renders fail or produce incorrect UI behavior
- xbmcgui.ListItem() has no copy constructor or serialization mechanism

**Original Assumption**: Cache ListItem objects built once, reuse across renders. Reality: Kodi forbids this by design.

**Decision**: Do not pursue. Architecturally impossible.

---

### Recipe Caching (Limited Gain) (DEFERRED)

**Why Deferred**: Theoretical ~20–35% gain is too small relative to API latency dominance.

**Technical Details**:
- Caching metadata dicts (not ListItems) could skip ~2–3ms of dict-building per item
- On a 50-item warm-cache menu: saves ~100–150ms of metadata processing
- However, API latency dominates: typical fetch 500–2000ms already exists
- **Real impact**: 100–150ms saving in 1000ms–2000ms total render = 5–15% improvement, mostly invisible to users

**Cache Footprint**:
- ~1–2KB per recipe × ~500 episodes = ~1MB additional cache space
- SimpleCache already growing with current episode/project caches

**Decision**: Defer until offscreen + measurement show that metadata overhead is actually a bottleneck. If API remains dominant, recipe caching is not worth the added complexity.

---

## Testing Strategy

- **Instrumentation tests**: Unit tests verify timing logs are emitted correctly (no false alarms)
- **Integration tests**: Manual smoke tests on large menus (continue watching, 50+ episodes, multiple seasons)
- **Performance baseline**: Collect timing data before and after offscreen=True to quantify GUI lock savings
- **Regression**: Verify art URLs, cast display, resume points, playback metadata intact after offscreen change

## Success Metrics

- **Phase 1 (Instrumentation)**: Timing logs clearly identify the dominant bottleneck (API, metadata, ListItem, or cache)
- **Phase 2 (Offscreen)**: 10–25ms improvement on large menus; user-facing responsiveness improved on loaded systems
- **Phase 3 (Data-Driven)**: Follow-up optimization targets the real bottleneck identified in Phase 1

## Risks & Mitigations

- **Risk**: Instrumentation logging becomes noisy; impacts performance
  - *Mitigation*: Use `debug()` level for per-item timings; `info()` for high-level totals; guard with log level checks
- **Risk**: Offscreen breaks art loading or causes threading issues
  - *Mitigation*: Easy rollback (remove offscreen=True); monitor Kodi logs; test on multiple skins before merging
- **Risk**: Measurement data shows that optimization is not worthwhile
  - *Mitigation*: Document findings and defer work; revisit if user reports improve performance feedback

## References

- Kodi ListItem API: https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html
- VideoInfoTag setters: https://codedocs.xyz/xbmc/xbmc/group__python__InfoTagVideo.html
- Kodi 20 release notes: https://kodi.wiki/view/Kodi_v20
- SimpleCache docs: Internal Kodi caching mechanism (via simplecache package)
- Current code: [kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py)

## Document History

- **2026-01-10**: Initial draft with three proposed optimizations
- **2026-01-12**: Updated with API research findings
  - Moved discarded ideas to separate section with explanations
  - Promoted offscreen mode to immediate recommendation
  - Added instrumentation & measurement plan
  - Shifted to data-driven optimization philosophy
- **2026-01-12**: Deferred Cache Write Optimization
  - **IMPLEMENTED & VALIDATED**: Moved cache writes after `endOfDirectory()` to defer until directory renders
  - Results: 33% improvement in Continue Watching menu responsiveness (2500ms → 1676ms avg)
  - Pattern enables future prefetching and cache pre-population optimization
  - See [DEFERRED_CACHE_WRITES.md](./DEFERRED_CACHE_WRITES.md) for architecture details

## Phase 1: Instrumentation ✅ COMPLETED

**Status**: Timing instrumentation fully implemented with [TIMING] prefix standardization.

### Measurements Collected

Real Kodi navigation session captured timing data across all menus:

| Menu | Calls | Avg Time | Per-Item | Key Finding |
|------|-------|----------|----------|-------------|
| **projects_menu** | 3 | 1452ms | 26.7ms | Movies ultra-fast (18.5ms), series slower (31ms) |
| **seasons_menu** | 7 | 262ms | 46.4ms | Fetch varies (2-385ms), render consistent |
| **episodes_menu** | 14 | 1441ms | 156.3ms | **BOTTLENECK**: 67% cache hit; 2x slower uncached |
| **continue_watching_menu** | 3 | 2500ms | 151ms | **CRITICAL**: 959ms cache writes blocking UI |

### Key Insights

1. **Episode metadata is expensive** (156ms per item) - dominates render time
2. **Cache writes were massive bottleneck** (584-1182ms) - now deferred
3. **Cache hits critical** - 67% hit rate; full hits 2x faster than misses
4. **API latency moderate** (225-482ms) - acceptable, not dominant bottleneck

## Phase 2: Deferred Cache Writes ✅ COMPLETED & VALIDATED

**Status**: Implemented in `continue_watching_menu()`, validated with real performance testing.

### Implementation

- Moved `cache.set()` operations to `_deferred_cache_write()` method
- Called **after** `xbmcplugin.endOfDirectory()` in same thread (non-blocking from UI perspective)
- Timing logs report `cache_write: deferred` to reflect user experience

### Performance Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Avg menu time** | 2500ms | 1676ms | **-33%** ✓ |
| **User-perceived delay** | 2.5s | 1.7s | **-32%** ✓ |
| **Cache write impact** | 959ms blocking | deferred | **-100% UI impact** ✓ |
| **Full session time** | ~33s | ~13s | **60% faster** 🚀 |

### Why It Works

- `endOfDirectory()` signals UI thread to render **in parallel** with Python execution
- Cache writes happen sequentially after UI renders (safe, no threading)
- SimpleCache synchronous operations safe for single-threaded addon model
- Partial cache acceptable (full cache on next API call if user navigates away)

### Pattern Enablement

This deferred approach unlocks future optimizations:
1. **Prefetching**: Background cache warming while user browses
2. **Cache pre-population**: Startup-time cache warming for fast first loads
3. **Batch operations**: Queue multiple cache operations post-render

## Phase 3: Next Optimization Targets

Based on measurement data, remaining bottlenecks are:

### Priority 1: Episode Metadata Rendering (156ms per item)
- **Bottleneck**: `_process_attributes_to_infotags()` metadata application
- **Hypothesis**: Cloudinary URL fetching for images during metadata setup
- **Approach**: Profile metadata function; identify hotspot; consider caching image URLs
- **Expected gain**: 20-30ms per item (10-15% improvement)

### Priority 2: Offscreen Mode for Directory Items
- **Bottleneck**: GUI lock contention during ListItem creation
- **Hypothesis**: Modest savings on loaded systems (~0.2-0.5ms per item)
- **Approach**: Add `offscreen=True` to ListItem constructors in all directory methods
- **Expected gain**: 10-25ms on 50-item menus (2-5% improvement)
- **Risk**: Low (already used for playback items)

### Priority 3: Cache Pre-population (Future)
- **Bottleneck**: First-load scenarios without cache
- **Hypothesis**: Warming cache during addon startup saves first menu load
- **Approach**: Background API calls on addon init to cache projects/episodes
- **Expected gain**: Near-instant first menu load (500-1000ms saved on first app launch)
- **Risk**: Medium (adds startup complexity; must be non-blocking)
