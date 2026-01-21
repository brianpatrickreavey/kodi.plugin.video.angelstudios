# Feature: Dedicated Player Class

**Date:** January 21, 2026
**Status:** Planning
**Owner:** Architecture & Product
**Audience:** Developer

---

## Executive Summary

This feature introduces a dedicated Player class to handle content playback and continuous watch position updates to the Angel Studios API. The goal is to centralize playback logic, improve resume functionality, and ensure accurate progress tracking.

**Scope:**
- Create Player class for content playback
- Implement watch position updates to Angel API
- Integrate with existing playback flow
- Handle resume functionality

**Risk Profile:** Medium (playback changes)

**Timeline Estimate:** 6-8 hours

**Success Criteria:**
1. Player class handles all playback operations
2. Watch positions updated to Angel API
3. Resume functionality improved
4. Backward compatibility maintained

---

## Current Playback Flow

**Current Implementation:**
- Playback initiated via `xbmcplugin.setResolvedUrl()`
- No continuous position tracking
- Resume based on cached data only

**Issues:**
- No real-time progress updates
- Resume data may be stale
- Playback logic scattered

---

## Player Class Design

### Core Responsibilities

1. **Playback Management:**
   - Handle video URL resolution
   - Set up Kodi player
   - Monitor playback state

2. **Progress Tracking:**
   - Track current position
   - Send updates to Angel API
   - Handle buffering/stopping

3. **Resume Functionality:**
   - Store last position
   - Resume from correct position
   - Sync with API data

### Class Structure

```python
class AngelPlayer:
    def __init__(self, angel_interface):
        self.angel_interface = angel_interface
        self.current_episode_guid = None
        self.last_position = 0

    def play_episode(self, episode_guid, resume=False):
        # Resolve URL, set up player, start monitoring

    def _on_playback_started(self):
        # Start position tracking

    def _on_playback_paused(self):
        # Update position

    def _on_playback_stopped(self):
        # Final position update

    def _update_watch_position(self, position):
        # Send to Angel API
```

### API Integration

**Watch Position Updates:**
- Use Angel API mutation for position updates
- Send periodic updates (every 30 seconds)
- Handle API failures gracefully

**Resume Data:**
- Fetch latest position from API
- Override cached data if newer
- Handle conflicts

---

## Implementation Steps

1. **Design Player Class:** Define interface and methods
2. **Implement Playback:** Handle URL resolution and Kodi player setup
3. **Add Position Tracking:** Monitor and update positions
4. **Integrate API Updates:** Send progress to Angel Studios
5. **Update Resume Logic:** Use API data for resume positions
6. **Test Integration:** Ensure compatibility with existing flow

---

## Acceptance Criteria

- [ ] Player class handles all playback operations
- [ ] Watch positions updated to Angel API
- [ ] Resume functionality uses latest API data
- [ ] No breaking changes to existing playback
- [ ] Position tracking accurate and reliable

---

## File Changes

- **New:** `resources/lib/player.py` (Player class)
- **Modified:** `resources/lib/kodi_ui_interface.py` (integrate Player)
- **Modified:** `resources/lib/angel_interface.py` (add position update methods)
- **New:** Unit tests for Player class