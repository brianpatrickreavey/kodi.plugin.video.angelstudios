# Infotags Processing (Direct Dict Access)

## Overview
This document describes the performance optimization implemented in `_process_attributes_to_infotags()` to reduce episode render time by 85-90%.

## Decision
Replaced generic loop with explicit attribute checks in `_process_attributes_to_infotags()`.

## Rationale
Eliminated 85-90% overhead from iterating 25+ dict keys per episode, which included unnecessary logging, string formatting, and conditional checks for unused attributes.

## Impact
- Episode render time: 33ms → 3-5ms (85-90% reduction)
- Menu render (50 episodes): 1,650ms → 150-250ms
- Overall menu responsiveness: Significantly improved for large episode lists

## Implementation Details
- **Direct dict access**: Explicit `if info_dict.get("key"):` checks instead of looping over all keys
- **Cloudinary URL reuse**: Builds URLs once and reuses for multiple art keys (e.g., logo for logo/clearlogo/icon)
- **Minimal logging**: Debug logs removed from hot path; performance timing available with "Enable performance logging" setting

## Constraints
- Manual updates required for new API attributes
- Assumes stable Angel Studios API v1 schema

## Files
- `kodi_menu_handler.py` (lines ~680–813)

## Metrics Source
Performance timing with `[PERF]` logs (enable with "Enable performance logging" setting).

## For Agents/AI
This is a performance-critical hot path. Avoid adding loops or per-key logging. If schema changes, update direct checks explicitly. Reuse URLs for art keys to avoid redundant API calls.