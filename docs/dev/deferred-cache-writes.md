# Deferred Cache Writes Pattern

## Overview

Deferred cache writes allow cache operations to complete **after** the Kodi directory is rendered, improving perceived UI responsiveness without sacrificing cache pre-population benefits.

## How It Works

### Execution Model

1. **Fetch** - Get data from API (blocking, necessary)
2. **Render** - Build and send directory items to Kodi UI
3. **Call `xbmcplugin.endOfDirectory()`** - UI thread renders immediately
4. **Deferred Writes** - Cache writes happen in same thread, but after UI is rendering (non-blocking from user perspective)
5. **Return** - Plugin handler cleanup

**Key insight**: `endOfDirectory()` doesn't suspend your code; it signals Kodi's UI thread to render in parallel while your Python execution continues.

### Why This Is Safe

- **Single-threaded execution**: Python code runs sequentially in plugin thread (not UI thread)
- **Independent UI thread**: Kodi's UI renders independently; cache writes don't interfere
- **SimpleCache is synchronous**: Operations complete atomically without threading concerns
- **Partial cache acceptable**: If user navigates away before writes complete, next API call will populate cache anyway

## Implementation

### Pattern

```python
def menu_with_caching(self, param):
    # Fetch data (blocking, unavoidable)
    data = self.api.get_data()

    # Render items (blocking, necessary)
    for item in data:
        list_item = self._create_item(item)
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

    # Log total time before cache writes (reflects UI responsiveness)
    total_time = time.perf_counter() - start
    self.log.info(f"[PERF] menu: {total_time:.1f}ms (cache_write: deferred)")

    # Signal directory complete (UI renders NOW)
    xbmcplugin.endOfDirectory(self.handle)

    # Cache writes happen after directory is rendered (parallel from user perspective)
    self._deferred_cache_write(data)

def _deferred_cache_write(self, data):
    """Non-blocking cache writes after directory rendering."""
    cache_start = time.perf_counter()

    for item in data:
        self.cache.set(f"item_{item['id']}", item, expiration=self._cache_ttl())

    cache_time = (time.perf_counter() - cache_start) * 1000
    self.log.debug(f"[PERF] _deferred_cache_write: {cache_time:.1f}ms ({len(data)} items)")
```

### Current Implementation

See [continue_watching_menu()](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py) for the production pattern:
- Fetches resume data (FAT query)
- Renders items immediately
- Calls `_deferred_cache_write()` after `endOfDirectory()`

## Timing Characteristics

From real Kodi navigation:
- **Typical cache write**: 584-1182ms (but deferred, so invisible to user)
- **Observed menu rendering**: < 1600ms (before deferred writes start)
- **User impact**: Responsive menu display (~1.5-1.6s) vs. stalled UI (2.5-3.0s with synchronous writes)

## Optimization Opportunities

This pattern enables powerful optimizations:

### 1. **Prefetching** (Future)
```python
# After endOfDirectory(), prefetch related data for next navigation
def _deferred_prefetch_project(self, project_slugs, max_count=None):
    """Prefetch project data in background."""
    for slug in project_slugs[:max_count]:
        try:
            project = self.angel_interface.get_project(slug)
            self.cache.set(f"project_{slug}", project, expiration=self._cache_ttl())
        except Exception:
            pass  # Silent failure - prefetch is optional
```

### 2. **Strategic Preloading**
- Prefetch data for most likely next navigation
- Example: After episodes_menu(), prefetch project data for parent project
- Cache hits become near-instantaneous

### 3. **Non-Blocking Image Prefetch**
- Download image URLs after menu renders
- Trigger Kodi's internal texture cache
- Images ready when user navigates to item

## Error Handling

**Cache write failures must never crash the plugin**:

```python
def _deferred_cache_write(self, data):
    try:
        for item in data:
            try:
                self.cache.set(f"item_{item['id']}", item, expiration=self._cache_ttl())
            except Exception as e:
                self.log.warning(f"Cache write failed for item {item['id']}: {e}")
                # Continue with next item
    except Exception as e:
        self.log.error(f"Deferred cache write failed: {e}")
        # Handler continues, next menu will re-fetch
```

## Integration Points

### episodes_menu()
- Fetch episodes via batch query
- Render menu items
- `endOfDirectory()`
- `_deferred_cache_write()` for batch-fetched episodes only
- (Skip cache-hit episodes to avoid redundant writes)

### projects_menu()
- Fetch projects
- Render menu items
- `endOfDirectory()`
- `_deferred_prefetch_project()` for uncached projects

### seasons_menu()
- Fetch single project with all seasons
- Render season items
- `endOfDirectory()`
- `_deferred_prefetch_episodes()` for all seasons' episodes

### continue_watching_menu()
- Fetch resume watching data (fat query)
- Extract episodes + projects
- Render items
- `endOfDirectory()`
- `_deferred_cache_write()` for episodes and projects

## Testing Strategy

### Unit Tests
- Mock `SimpleCache` to verify cache.set() calls
- Verify deferred writes collect correct data
- Test error handling (exceptions during write don't crash)

### Integration Tests
- Verify real cache writes work
- Confirm timing: endOfDirectory() called before writes
- Test with actual Kodi API interaction

### Performance Tests
- Measure menu render time (before endOfDirectory())
- Measure total plugin handler time (including deferred work)
- Confirm render time << total time (deferred work invisible to user)

## Monitoring

Track deferred cache performance:

```python
# In kodi_ui_interface.py
self.log.info(f"[PERF] menu: {render_time:.1f}ms (cache_write: deferred)")
self.log.debug(f"[PERF] _deferred_cache_write: {cache_time:.1f}ms ({len(data)} items)")
```

Examples from production:
- `continue_watching_menu COMPLETED in 1287ms (fetch: 950ms, cache_write: deferred, render: 128ms)`
- `_deferred_cache_write completed in 1170.6ms (10 episodes, 10 projects)`

User sees menu at ~1.3s; cache write happens invisibly from 1.3s to 2.5s.

## Rollback Plan

If deferred writes cause issues:
1. Remove `_deferred_cache_write()` call
2. Restore synchronous cache writes in menu loop
3. Trade-off: UI responsiveness for cache pre-population (accept higher total time)

## References

- [TIMING_INSTRUMENTATION.md](../TIMING_INSTRUMENTATION.md) - Timing infrastructure
- [kodi_ui_interface.py](../plugin.video.angelstudios/resources/lib/kodi_ui_interface.py) - Production implementation
- [Kodi plugin lifecycle](https://kodi.wiki/view/Add-on_development) - Understanding endOfDirectory()
