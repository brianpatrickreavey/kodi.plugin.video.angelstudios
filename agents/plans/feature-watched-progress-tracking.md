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

## Technical Implementation

### Current Progress Retrieval
- **API Integration**: `getEpisodeAndUserWatchData` GraphQL query retrieves existing progress
- **Resume Points**: `watchPosition { position }` field provides current playback position
- **Display**: Progress bars applied via `info_tag.setResumePoint(position / duration)`

### Planned Progress Updates
- **API Endpoint**: GraphQL mutation to update watch position (when available from Angel Studios)
- **Update Triggers**: Send progress updates during playback at regular intervals
- **Data Format**: Position in seconds, episode GUID, and user authentication
- **Error Handling**: Graceful handling of API failures without interrupting playback

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