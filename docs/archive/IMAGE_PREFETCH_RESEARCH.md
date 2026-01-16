# Image Prefetch Research & Strategy

**Date**: January 14, 2026
**Status**: ❌ INVESTIGATION CONCLUDED - NOT VIABLE
**Objective**: ~~Eliminate image loading lag in Kodi menus by prefetching Cloudinary URLs~~
**Conclusion**: Accept Kodi's native TextureCache behavior - no manual prefetch possible

---

## EXECUTIVE SUMMARY - Investigation Results

**Bottom Line**: Image prefetch via Python is **NOT VIABLE**. Kodi's TextureCache operates independently from Python's HTTP stack.

**What We Tested**:
1. ✅ Implemented test menu with HTTP prefetch via `requests.head()`
2. ✅ Executed clean-cache test with network monitoring (tcpdump)
3. ✅ Analyzed YouTube plugin codebase for reference implementation
4. ✅ Investigated Kodi source code for manual TextureCache trigger APIs

**What We Found**:
- **HTTP Isolation**: Python's `requests` library and Kodi's TextureCache use separate HTTP stacks (urllib3 vs libcURL)
- **Network Evidence**: tcpdump showed TWO separate waves of HTTP traffic:
  - 09:59:26.155-09:59:26.405: Plugin's prefetch via requests (2 connections)
  - 09:59:27.xxx: Kodi's TextureCache fetching when user highlighted items
- **No API Exists**: Kodi has no Python API to manually trigger TextureCache caching
  - `offscreen=True` is GUI locking only, NOT texture pre-rendering (confirmed in ListItem.h)
  - JSON-RPC TextureOperations only query/remove, no add/cache methods
  - BackgroundCacheImage() is internal C++ only, no Python binding
- **YouTube Plugin**: Does NOT implement image prefetch - relies on natural Kodi caching (same as our current behavior)

**Current Achievement**: 95-98% performance improvement already delivered through data processing optimization (30-50ms → 0.6-1.7ms per item).

**Recommendation**: Accept Kodi's native caching behavior. Images cache automatically on first display and are instant on subsequent views. This is the pattern used by all major Kodi plugins.

---

## 1. Project Architecture Findings

### Current State - Data Prefetch Already Implemented ✓

- **Location**: `plugin.video.angelstudios/resources/lib/kodi_ui_interface.py`
- **Methods**:
  - `_deferred_prefetch_project()` (line 1274)
  - `_deferred_prefetch_episodes()` (line 1333)
- **Pattern**: Prefetch happens AFTER `endOfDirectory()` call (deferred execution model)
- **Status**: Actively used in `projects_menu()` and `seasons_menu()`
- **Reference**: See `/agents/plans/cache-optimization-deferred-writes-prefetch.md`

### Key Distinction: Data vs Image Prefetch

| Aspect | Data Prefetch | Image Prefetch |
|--------|--------------|----------------|
| **What** | Project/episode metadata via GraphQL | Actual image files (JPG/PNG) from Cloudinary |
| **Status** | ✓ Already implemented | ✗ Not yet implemented |
| **Timing** | API calls (500-2000ms baseline) | HTTP GET requests for image bytes |
| **Current Gap** | N/A | Only URLs passed to setArt(); images not downloaded until user highlights |

---

## 2. Kodi Image Caching Mechanism

### TextureCache Architecture

**Found in**: `~/Code/xbmc/xbmc/TextureCache.cpp`

**Key Function**: `BackgroundCacheImage(const std::string& url)`

```cpp
void CTextureCache::BackgroundCacheImage(const std::string &url)
{
  if (url.empty())
    return;

  CTextureDetails details;
  std::string path(GetCachedImage(url, details));
  if (!path.empty() && details.hash.empty())
    return; // image is already cached

  path = IMAGE_FILES::ToCacheKey(url);
  if (path.empty())
    return;

  // needs (re)caching
  AddJob(new CTextureCacheJob(path, details.hash));
}
```

**How It Works**:
1. Call receives a URL
2. Checks if image already cached locally
3. If not cached: Adds async job to Kodi's texture cache queue
4. Job executes in background (non-blocking)
5. Once cached: Subsequent `setArt()` calls use local cached file

### Python API Exposure Status

| Mechanism | Exposed to Python | Notes |
|-----------|------------------|-------|
| `BackgroundCacheImage()` | ✗ NO | Internal C++ API, not exposed to addon plugins |
| Direct texture cache access | ✗ NO | No Python method for programmatic cache control |
| `setArt()` with URLs | ✓ YES | Standard Kodi Python API (xbmcgui.ListItem.setArt) |
| HTTP prefetch workaround | ✓ YES | Manual HTTP request can trigger cache detection |

---

## 3. Current Plugin Implementation

### setArt() Usage Pattern

**Location**: `kodi_ui_interface.py` lines 386, 1697

```python
# Example 1: Menu items
list_item.setArt({"icon": item["icon"], "thumb": item["icon"]})

# Example 2: Episode items
if art_dict:
    list_item.setArt(art_dict)
```

**Current Timing**:
- Called DURING menu render (before `endOfDirectory()`)
- Images NOT cached until user highlights item in Kodi UI
- Cloudinary URLs generated in ~0.6-1.7ms (after optimization)
- Problem: URLs ready immediately, but images not downloaded

### Cloudinary URL Generation

**Source**: `angel_interface.py` line 208
**Method**: `get_cloudinary_url(cloudinary_path)`
**Format**: `https://images.angelstudios.com/image/upload/{cloudinary_path}`
**Performance**: Generated on-demand during `_process_attributes_to_infotags()`

### Plugin Execution Model (Confirmed)

```
┌─ Plugin Handler Starts
│
├─ Fetch API data (blocking, ~500-2000ms)
│
├─ For each item:
│   ├─ Create ListItem
│   ├─ Call setArt() with Cloudinary URL
│   ├─ Add to Kodi directory
│   └─ (Image NOT downloaded yet)
│
├─ Call xbmcplugin.endOfDirectory()
│   └─ (UI RENDERS HERE - user sees menu)
│
├─ [Deferred Work Can Execute Here]
│   ├─ Cache writes (ALREADY IMPLEMENTED)
│   ├─ Data prefetch (ALREADY IMPLEMENTED)
│   └─ [IMAGE PREFETCH GOES HERE]
│
└─ Handler returns
```

**Key Insight**: User sees rendered menu immediately after `endOfDirectory()`, while Python code continues executing deferred work.

---

## 4. Image Prefetch Strategy Options

### Option A: Manual HTTP Prefetch (RECOMMENDED)

**Mechanism**:
1. After `endOfDirectory()` call
2. For each rendered image URL:
   - Use `requests.head(url)` or `requests.get(url)` to fetch
   - Cloudinary delivers image bytes
   - Kodi monitors HTTP traffic and detects URLs
   - May trigger internal TextureCache caching

**Advantages**:
- ✓ Works without Kodi C++ API exposure
- ✓ Follows existing prefetch pattern (deferred execution)
- ✓ Can be rate-limited and made non-blocking
- ✓ Gracefully handles interruptions (stop if user navigates away)

**Disadvantages**:
- ✗ Uncertain if HTTP prefetch triggers Kodi's TextureCache
- ✗ Uses extra bandwidth (especially if images already cached)
- ✗ May need verification/testing to confirm effectiveness

**Implementation**:
```python
def _prefetch_images(self, image_urls, max_concurrent=3):
    """Prefetch images in background after menu renders."""
    for url in image_urls[:max_concurrent]:  # Limit concurrent
        try:
            requests.head(url, timeout=5)  # HEAD request is faster
            self.log.debug(f"[PREFETCH] Image URL fetched: {url[:50]}...")
        except Exception as e:
            self.log.debug(f"[PREFETCH] Image fetch failed (will retry on highlight): {e}")
```

### Option B: Rely on Highlight Trigger (CURRENT)

**How it works**:
- Images fetched when user highlights item
- Kodi's rendering engine detects image URLs and downloads
- No prefetch logic needed

**Problem**: First navigation shows no images until user highlights

### Option C: Research xbmc.renderAddon (UNCERTAIN)

**Status**: Not found in current xbmc source search
**May be**: Kodi 20+ feature for image rendering/caching
**Action**: Would require deeper xbmc API investigation
**Feasibility**: Lower priority, more research needed

---

## 5. Integration Points for Image Prefetch

### Location 1: After `_process_attributes_to_infotags()` (RISKY)

- URLs ready in ~0.6-1.7ms
- Could prefetch before `setArt()` call
- **Risk**: Image fetch might block menu rendering (defeating the purpose)
- **Not recommended**: Would reduce perceived responsiveness

### Location 2: After `endOfDirectory()` (RECOMMENDED)

- Menu already rendered and visible to user
- Background work is truly non-blocking
- Follows existing deferred prefetch pattern
- Safe to interrupt if user navigates away
- **Recommended**: Implements non-blocking prefetch

### Menu Methods to Enhance

| Menu | Item Count | Priority |
|------|-----------|----------|
| `episodes_menu()` | 12-50 episodes | HIGH - Critical UX pain point |
| `projects_menu()` | 5-20 projects | MEDIUM - Less frequent navigation |
| `continue_watching_menu()` | 10-20 mixed items | MEDIUM - Important for casual users |

---

## 6. Existing Project Documentation

### Related Plans & Docs

**Cache Optimization Plan**:
- Location: `/agents/plans/cache-optimization-deferred-writes-prefetch.md`
- Coverage: Data prefetch strategy, deferred execution pattern
- Useful: Template for image prefetch implementation

**Menu Optimization Plan**:
- Location: `/agents/plans/menu_optimization.md`
- Key Finding: API latency is real bottleneck, image loading is secondary
- Useful: Context for why image prefetch matters

**Deferred Cache Writes**:
- Location: `/docs/DEFERRED_CACHE_WRITES.md`
- Coverage: Explains deferred execution model, timing characteristics
- Useful: Production patterns for non-blocking operations

---

## 7. Implementation Readiness

### Dependencies Already Available ✓

| Dependency | Status | Usage |
|-----------|--------|-------|
| `requests` library | ✓ Imported | GraphQL/API calls (can reuse for image fetch) |
| Session object | ✓ Available | From `angel_authentication.py` (authenticated requests) |
| Logging infrastructure | ✓ Ready | KodiLogger with trace support |
| SimpleCache | ✓ Available | Could track prefetch state if needed |
| Timing instrumentation | ✓ Exists | `time.perf_counter()` already in use |

### Configuration Needed

Suggest adding to `resources/settings.xml`:

```xml
<!-- Image Prefetch Settings -->
<setting id="enable_image_prefetch" type="boolean" default="true">
    <label>30200</label>  <!-- Enable image prefetch -->
    <help>30201</help>    <!-- Prefetch images in background -->
</setting>

<setting id="max_concurrent_image_fetches" type="integer" default="3">
    <label>30202</label>  <!-- Max concurrent image downloads -->
    <constraints min="1" max="10" />
</setting>

<setting id="image_prefetch_timeout" type="integer" default="5">
    <label>30203</label>  <!-- Image fetch timeout (seconds) -->
    <constraints min="1" max="30" />
</setting>
```

### Testing Approach

**Unit Tests**:
- Mock `requests.head()` / `requests.get()`
- Verify calls made with correct URLs
- Verify error handling (failed fetches don't crash)

**Integration Tests**:
- Verify image URLs extracted from real episode data
- Confirm prefetch executes after `endOfDirectory()`
- Test with real Cloudinary URLs (if allowed)

**Manual Testing**:
- Navigate menus in Kodi
- Verify images appear immediately without flashing/loading
- Compare UX before/after prefetch

---

## 8. Test Results & Findings (January 14, 2026)

### Test 1: HTTP Prefetch with Network Monitoring ❌ NEGATIVE

**Test Setup**:
- Cleared Kodi texture cache completely (`~/.kodi/userdata/Thumbnails/`)
- Implemented test menu with `requests.head()` prefetch
- Ran tcpdump to monitor ALL HTTP traffic
- Executed test and highlighted menu items

**Results**:
```
09:59:26.155-09:59:26.405: Plugin's requests.head() prefetch (2 HTTP connections)
  - 200 OK responses in 114-148ms
  - Python requests → urllib3 → Network

09:59:27.xxx: Kodi's image fetching when user highlighted items
  - Massive additional HTTP traffic
  - Kodi TextureCache → libcURL → Network
```

**Conclusion**: Python HTTP requests and Kodi's TextureCache use **isolated HTTP stacks**. Prefetch via `requests` does NOT trigger Kodi's cache.

---

### Test 2: Kodi API Investigation ❌ NO API EXISTS

**Investigated APIs**:

| API | Purpose | Python Exposed | Findings |
|-----|---------|----------------|----------|
| `offscreen=True` | GUI locking | ✓ Yes | Only affects GUI thread locking, NOT texture caching (confirmed in ListItem.h lines 68-92) |
| JSON-RPC TextureOperations | Cache management | ✓ Yes | Only GetTextures/RemoveTexture - no add/cache methods (TextureOperations.cpp) |
| `BackgroundCacheImage()` | Async cache trigger | ✗ NO | Internal C++ only, no Python binding (TextureCache.cpp) |
| CacheTexture functions | Direct cache control | ✗ NO | Internal texture system, no API exposure |

**Conclusion**: Kodi provides **NO Python API** to manually trigger TextureCache caching.

---

### Test 3: YouTube Plugin Analysis ❌ NO PREFETCH IMPLEMENTED

**Investigated**: `/home/bpreavey/Code/plugin.video.youtube/`

**Findings**:
```python
# From xbmc_items.py lines 767-778
list_item = xbmcgui.ListItem(**kwargs)
image = media_item.get_image()
art = {'icon': image}
if image:
    art['thumb'] = image
if show_fanart:
    art['fanart'] = media_item.get_fanart()
list_item.setArt(art)
```

**Pattern**: Identical to our implementation - simple `setArt()` with URLs, **no prefetch logic**.

**Conclusion**: The widely-used YouTube plugin (millions of users) **does NOT implement image prefetch**. They rely on Kodi's natural caching behavior.

---

## 9. Technical Architecture Reality

### The Two HTTP Stacks

```
┌─────────────────────────────────────────────────────────┐
│ Python Plugin (plugin.video.angelstudios)               │
│                                                          │
│  requests.head(url)                                     │
│       ↓                                                  │
│  urllib3/httplib                                        │
│       ↓                                                  │
│  [HTTP Request] ──────────────────────→ Network         │
│                                                          │
│  (ISOLATED - Kodi doesn't see this)                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Kodi Core (C++)                                          │
│                                                          │
│  ListItem.setArt(url) → Rendering Engine                │
│       ↓                                                  │
│  TextureCache.BackgroundCacheImage()                    │
│       ↓                                                  │
│  libcURL                                                │
│       ↓                                                  │
│  [HTTP Request] ──────────────────────→ Network         │
│                                                          │
│  (AUTOMATIC - Triggered on first display)               │
└─────────────────────────────────────────────────────────┘
```

**Key Insight**: These are **completely separate systems**. Python cannot influence Kodi's TextureCache.

---

## 10. Final Recommendation

### Accept Kodi's Native Caching Behavior ✅

**Why This is OK**:
1. **Industry Standard**: YouTube plugin uses same approach
2. **Automatic Caching**: Kodi caches images on first display, instant on subsequent views
3. **Already Optimized**: 95-98% performance improvement achieved through data processing optimization
4. **User Experience**: Current bottleneck is data processing (solved), not image loading
5. **No Alternative**: No Python API exists to manually trigger caching

**Current Performance**:
- Data processing: 0.6-1.7ms per item (was 30-215ms) ✓
- Image loading: On-demand first view, cached thereafter ✓

### Optional: Keep Test Menu for Debugging

The test menu implementation can be kept in debug mode as a diagnostic tool:
- Helps verify image URLs are valid
- Useful for troubleshooting Cloudinary issues
- No performance impact (only visible in debug mode)
- Consider adding documentation comment explaining negative test results

---

## 11. Lessons Learned

1. **Isolated Stacks**: Python's HTTP libraries and Kodi's TextureCache are completely isolated
2. **No Manual Control**: Kodi's TextureCache is automatic-only, no manual trigger API
3. **Trust Native Behavior**: Major plugins rely on Kodi's automatic caching
4. **Optimize What Matters**: Data processing (solved) had bigger impact than image caching
5. **Test Before Implement**: Network monitoring proved hypothesis incorrect before significant implementation

---

## 12. Test Artifacts

**Evidence Files** (archived):
- `prefetch.log` - Plugin's HTTP prefetch execution logs
- `network.log` - tcpdump capture showing two separate HTTP traffic waves
- `kodi.log` - Kodi debug logs from clean-cache test
- Test implementation in `kodi_ui_interface.py` lines 892-973 (can be removed or kept for debugging)

---

## Historical Context (Pre-Investigation)

The sections below document the original research plan and strategy options that were explored before testing proved them non-viable.

---

## 1. Project Architecture Findings
