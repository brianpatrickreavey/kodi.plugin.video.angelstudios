# Performance Instrumentation Plan

**Objective:** Implement configurable performance logging to measure bottlenecks in menu loading (e.g., slow projects menus) without cluttering code. Gather data to reassess optimizations like deferred cache writes.

**Status:** Completed - implementation done, tests pass.

**Date:** January 19, 2026

---

## Background
Projects menus (series, movies, dry bar) are loading slowly. Previous timing metrics regressed during cleanup. Deferred cache writes may have been lost and need reassessment with data.

## Approach
Use a hybrid of decorators (function-level) and context managers (block-level) for clean, configurable timing:
- **Setting:** `enable_performance_logging` (bool, default false) in settings.xml.
- **Decorator:** `@timed` for entire methods (e.g., menu functions).
- **Context Manager:** `TimedBlock` for sub-blocks (e.g., API fetches within methods).
- **Output:** Kodi logs with `[PERF]` prefix at `LOGINFO` level when enabled; silent otherwise. Users must set Kodi's log level to `INFO` or `DEBUG` to see logs.

## Implementation Steps

### Step 1: Add Setting
**File:** `resources/settings.xml`
**Change:** Add bool setting `enable_performance_logging` with label "Enable performance logging" and default false.

### Step 2: Create Performance Utilities
**File:** `resources/lib/kodi_utils.py` (or new `performance_utils.py`)
**Add:**
- `@timed` decorator: Wraps functions, logs total time if setting enabled.
- `TimedBlock` context manager: Wraps code blocks, logs elapsed time if setting enabled.

### Step 3: Apply to Key Methods
**Files:** `resources/lib/kodi_ui_interface.py`
**Methods to instrument:**
- `projects_menu()`: API fetch, cache checks, UI rendering.
- `seasons_menu()`: Similar breakdown.
- `episodes_menu()`: Cache writes, rendering.
- `continue_watching_menu()`: Fat query, normalization, rendering.
**Use:** Decorator on methods + context managers inside for granularity.

### Step 4: Test and Validate
- Enable setting, run menus, check logs for timing output.
- Disable setting, verify no overhead.
- Ensure no impact on production performance.

### Step 5: Document
**File:** `/docs/dev/performance-instrumentation.md`
**Content:** How to use, examples, analysis tips.

## Success Criteria
- Timing logs appear only when enabled.
- No code clutter; easy to add/remove.
- Provides data on API vs. cache vs. UI bottlenecks.
- Helps decide on deferred writes/prefetch.

## Risks
- Minor overhead if enabled (time.perf_counter() calls).
- Log spam if overused.

## For Agents/AI
Enable performance logging to measure menu bottlenecks; use decorators for methods, context managers for blocks.