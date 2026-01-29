# Watched Progress Tracking Feature

## Overview
The Watched Progress Tracking feature would enable the Kodi plugin to send watch progress updates back to Angel Studios servers, allowing users to resume playback across different devices and maintain synchronized progress.

## Current Implementation Status

### ✅ Completed Features
- **Resume Dialog**: Kodi displays native resume dialog when playing episodes with existing progress
- **Progress Display**: Continue Watching menu shows in-progress episodes with progress bars
- **Local Progress Bars**: Native Kodi progress indicators on episode list items

### 🔄 Planned Features
- **Progress Updates**: Send watch position updates to Angel Studios API during playback
- **Cross-Device Sync**: Resume playback on different devices where you left off
- **Progress Persistence**: Maintain accurate progress even after Kodi restarts

## Implementation Approach

### Dedicated Player Class
To implement progress tracking, a dedicated `AngelPlayer` class will be created to centralize playback logic and handle continuous position updates.

**Core Responsibilities:**
1. **Playback Management:** Handle video URL resolution and Kodi player setup
2. **Progress Tracking:** Monitor current position and send updates to Angel API
3. **Resume Functionality:** Store last position and sync with API data

**Class Structure:**
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

**API Integration:**
- Send periodic updates every 30 seconds during playback
- Handle API failures gracefully without interrupting playback
- Fetch latest position from API to override cached data when resuming

## User Experience Benefits

### Seamless Playback
- **Cross-Device Continuity**: Start watching on one device, continue on another
- **Progress Preservation**: Never lose track of where you left off
- **Unified Experience**: Consistent progress across Angel Studios web and Kodi

### Playback Integration
- **Resume Prompts**: Kodi's native "Resume from X%" dialogs
- **Progress Indicators**: Visual progress bars in episode lists
- **Accurate Tracking**: Precise position tracking for long-form content

## Implementation Requirements

### Angel Studios API
- **Mutation Endpoint**: GraphQL mutation for updating watch progress
- **Authentication**: Valid JWT token required for progress updates
- **Rate Limiting**: Appropriate throttling to prevent API abuse
- **Data Validation**: Server-side validation of position and episode data

### Kodi Integration
- **Playback Monitoring**: Track playback position during video playback
- **Update Frequency**: Send updates at appropriate intervals (every 30-60 seconds)
- **Background Processing**: Non-blocking progress updates that don't interrupt playback
- **Offline Handling**: Queue updates when offline, send when connection restored

## Technical Challenges

### Playback Position Accuracy
- **Seek Handling**: Properly handle user seeking forward/backward
- **Buffering**: Account for buffering delays in position reporting
- **Completion Detection**: Mark episodes as completed when finished

### API Integration
- **Endpoint Discovery**: Identify correct GraphQL mutation for progress updates
- **Authentication Flow**: Ensure valid session for progress updates
- **Error Recovery**: Handle network failures and API errors gracefully

## Status
**Waiting on Angel Studios API**: Implementation blocked until progress update endpoints are available. Current functionality provides local progress display and resume capabilities, with server-side synchronization planned for future implementation.

## Related Features
- **Continue Watching**: Depends on progress tracking for accurate episode ordering
- **Authentication**: Required for sending progress updates to user accounts
- **Playback Handler**: Core component for monitoring and reporting progress