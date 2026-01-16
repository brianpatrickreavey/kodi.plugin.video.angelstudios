# Timing Instrumentation Implementation

**Date**: 2026-01-12
**Status**: ✅ Complete and tested

## Overview

Performance measurement instrumentation has been added to menu rendering methods to identify actual bottlenecks (API latency, ListItem creation, metadata application, etc.) before pursuing optimization strategies.

## What Was Instrumented

### Menu Methods (High-Level Timing)
Added `time.perf_counter()` instrumentation around:

1. **`continue_watching_menu(after=None)`**
   - Total time + API fetch time + cache write time + render time
   - Per-item render time (debug log)
   - Cache hits/misses analysis

2. **`projects_menu(content_type="")`**
   - Total time + fetch time (source: cache vs. API) + render time
   - Per-item time (debug log)

3. **`seasons_menu(content_type, project_slug)`**
   - Total time + fetch time + render time
   - Per-item time (debug log)

4. **`episodes_menu(content_type, project_slug, season_id=None)`**
   - Total time with breakdown:
     - Project fetch time
     - Episode cache check time
     - Batch fetch time (for cache misses)
     - Render time
   - Cache hit/miss ratio
   - Per-item render time (debug log)

### Helper Methods (Granular Timing)

1. **`_process_attributes_to_infotags(list_item, info_dict)`**
   - Per-call timing (trace log only, ~0.1-1ms typical)
   - Identifies metadata application overhead

2. **`_create_list_item_from_episode(...)`**
   - Called from menu loops; timing already measured at call site
   - Includes playback setup, ISA detection, stream details

## Log Format

### High-Level Logs (INFO level)
```
[INFO] continue_watching_menu: START (cache enabled: True, after=None)
[DEBUG] Fetched 10 items in 1023ms (API call: 950ms, cache write: 73ms)
[INFO] continue_watching_menu: Completed in 1287ms (fetch: 1023ms, cache_write: 73ms, render: 191ms, 10 items, 19.1ms/item)
```

### Per-Item Logs (DEBUG level, trace mode only)
```
[TRACE] Item 1: 12.3ms
[TRACE] Item 2: 11.8ms
[TRACE] _process_attributes_to_infotags completed in 0.5ms
```

### Episodes Menu with Cache Hits
```
[INFO] episodes_menu: COMPLETED in 2150.5ms (fetch_project: 50.2ms, cache_check: 25.3ms, batch_fetch: 1950.0ms, render: 125.0ms, 40 items, 3.1ms/item, cache_hits: 15/40)
```

## Activation

All timing logs use:
- **INFO level**: High-level metrics (method entry/exit, phase breakdown, totals)
- **DEBUG level**: Fetch/cache details, item counts
- **TRACE level**: Per-item timings (only if debug_mode=trace in settings)

## Key Metrics Captured

1. **Total menu render time** - End-to-end menu display
2. **Fetch time breakdown**:
   - API call time
   - Cache read/write time
   - Batch fetch time
3. **Render time** - ListItem creation + metadata + art per item
4. **Per-item averages** - (render_time / item_count)
5. **Cache hit ratio** - Episodes from cache vs. batch-fetched

## Testing

✅ All 312 unit tests pass
✅ 99% code coverage maintained (5 lines missed: trace-mode conditionals)
✅ Syntax validation passed
✅ No breaking changes to existing API or behavior

## Next Steps

1. **Collect Timing Data**: Navigate menus in Kodi and observe logs
   - Cold cache (first load): captures API latency
   - Warm cache (repeat load): shows metadata + ListItem overhead
   - Large menus (50+ items): shows per-item averages

2. **Analyze Results**: Identify which section dominates
   - If API > 90%: Focus on batch queries, image caching, parallel API
   - If metadata > 50%: Consider recipe caching or dict optimization
   - If ListItem > 50%: Evaluate pagination or async rendering

3. **Implement Offscreen=True**: Phase 2 of optimization plan
   - Safe, low-risk change
   - Expected 10-25ms improvement on 50-item menus
   - Can be tested independently

## Files Modified

- `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
  - Added timing instrumentation to 6 methods
  - Total lines added: ~120 (mostly logging)
  - No changes to core logic or API

## Backward Compatibility

✅ Fully backward compatible
- No API changes
- Timing is logged, never returned or stored
- Can be disabled by setting debug_mode=off in addon settings
- No performance impact when logs are not collected (INFO level always enabled)
