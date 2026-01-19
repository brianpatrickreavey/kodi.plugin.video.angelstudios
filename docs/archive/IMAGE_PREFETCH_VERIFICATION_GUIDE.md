# Image Prefetch Verification Guide

**Status**: Investigation concluded — HTTP prefetch via Python does **not** trigger Kodi's TextureCache. This guide is retained only to reproduce the negative result and for future diagnostics.

## Overview

Note: The debug test menu was removed during cleanup; keep this guide for historical/reference purposes. If you need to reproduce the test, temporarily restore the removed debug menu code.

## Why This Matters

Data processing has already been optimized by 95-98% (30-50ms → 0.6-0.8ms). Image loading remains on-demand. Testing confirmed that HTTP prefetch does **not** warm Kodi’s cache; Kodi still fetches via libcURL on first highlight.

## Prerequisites

1. **Enable libcURL Logging in Kodi** (captures all HTTP requests):
   - Navigate: `Settings` → `System` → `Logging` → `Component Specific Logging`
   - Enable: `libcURL` (this logs all HTTP requests)
   - Log location varies by OS:
     - **Linux**: `~/.kodi/temp/kodi.log`
     - **Windows**: `%APPDATA%\kodi\temp\kodi.log`
     - **macOS**: `~/Library/Logs/kodi.log`
   - libcURL will capture:
     - Your plugin's `requests.head()` prefetch calls
     - Any subsequent TextureCache background downloads

2. **Enable Debug Mode in Angel Studios Addon**:
   - In addon settings, set Debug Mode to `Debug` or `Trace`
   - This makes the `[DEBUG] Test Image Prefetch` menu item visible

## Running the Test

### Step 1: Navigate to Test Menu
1. In Kodi, browse to Angel Studios addon
2. Main menu should show: **[DEBUG] Test Image Prefetch**
3. Select it

### Step 2: Observe Image Loading
When the test menu renders, watch for:

**Visual Test:**
- Do the two test images appear **immediately** when you scroll through items?
  - **YES** → Images likely cached (HTTP prefetch working ✓)
  - **NO** → Images load slowly/on-demand (HTTP prefetch not effective ✗)

**Timing Test:**
- Navigate to another menu, then **back** to the test menu
- Do images load instantly on return?
  - **YES** → TextureCache retained them between visits ✓
  - **NO** → Images must reload (not cached) ✗

### Step 3: Generate Log File
1. After running the test menu, close Kodi
2. Locate the `kodi.log` file (see Prerequisites for location)
3. Open it in a text editor and search for:
   - `libcURL` entries containing the Cloudinary domain (`res.cloudinary.com`)
   - `TEST-PREFETCH` (addon diagnostic logs)
   - Compare timing of requests to understand prefetch → cache flow

## Expected Log Output (Observed Result)

### What we actually see (confirmed failure):
```
09:59:26.xxx: Plugin prefetch via requests.head() (urllib3 stack)
09:59:27.xxx: Kodi TextureCache fetches same URLs via libcURL when items are highlighted
```

**Interpretation:** Two distinct waves of HTTP traffic prove isolation between Python HTTP and Kodi TextureCache. Prefetch does not prevent Kodi from re-fetching.

### If you re-run the test and see the same pattern
- This confirms expected behavior (negative outcome). Kodi will still fetch on first highlight.

### If you ever see only one wave
- Capture logs and timings; this would contradict current findings and would merit deeper investigation.

### Addon Diagnostic Output:
```
[TEST-PREFETCH] Starting image prefetch verification test
[TEST-PREFETCH] Test 1: Prefetching via requests.head() (baseline)
[TEST-PREFETCH] URL 1 prefetched: 200 in 245.3ms
[TEST-PREFETCH] URL 2 prefetched: 200 in 187.2ms
[TEST-PREFETCH] Creating test menu items
[TEST-PREFETCH] Test menu rendered. Check:
[TEST-PREFETCH] 1. Do images appear immediately when navigating back to menu?
[TEST-PREFETCH] 2. Check Kodi logs for libcURL entries matching test URLs
[TEST-PREFETCH] 3. See IMAGE_PREFETCH_RESEARCH.md in addon docs for analysis guide
```

## Analysis: How to Interpret Results

### Test Images Used
1. Angel Studios logo: `https://res.cloudinary.com/.../angel-studios-v2-header-c1b4b39b.jpg`
2. War of the Worms: `https://res.cloudinary.com/.../war-of-the-worms-v2-header-bf6db996.jpg`

### Decision Tree

```
Does image appear immediately when scrolling?
├─ YES, instantly visible
│  └─ Does it appear on second visit to menu?
│     ├─ YES → TextureCache worked, HTTP prefetch effective ✓✓✓
│     └─ NO → One-time cache, verify with logs
│
└─ NO, loads on highlight
   └─ Check kodi.log for TextureCache events
      ├─ Events found → HTTP works but timing issue
      └─ No events → HTTP prefetch not triggering cache
```

## Current Decision

- Prefetch via Python is **not** viable for warming Kodi’s TextureCache.
- We rely on Kodi’s native behavior: first highlight fetches via libcURL, subsequent views are cached.
- The debug test menu stays gated under debug/trace for diagnostics only; no production prefetch rollout planned.

## Troubleshooting

### "Test Image Prefetch" menu item doesn't appear
- Confirm Debug Mode is set to `Debug` or `Trace` in addon settings
- Reload addon (disable/enable or restart Kodi)

### Images still appear to load slowly
- Check `kodi.log` for libcURL errors (network issues, timeouts)
- Verify Cloudinary URLs are accessible (test in browser)
- Check Kodi TextureCache settings: `Settings` → `Media` → `General` → `Cache`

### No libcURL entries in logs
- Confirm libcURL logging is enabled (see Prerequisites)
- Check log file location is correct for your OS
- Some Kodi versions require restart after enabling logging
- Search for `res.cloudinary.com` specifically to find image requests

## References

- **IMAGE_PREFETCH_RESEARCH.md**: Full research on Kodi's TextureCache architecture
- **DEFERRED_CACHE_WRITES.md**: Understanding deferred execution model
- **TIMING_INSTRUMENTATION.md**: How the addon measures performance
- **Kodi TextureCache docs**: https://kodi.wiki/view/Texture_cache

## Questions?

If results are inconclusive or need verification:
1. Save both `kodi.log` and addon logs
2. Note the exact timing and behavior observed
3. Compare against expected output documented above
4. Consult IMAGE_PREFETCH_RESEARCH.md for deeper technical analysis
