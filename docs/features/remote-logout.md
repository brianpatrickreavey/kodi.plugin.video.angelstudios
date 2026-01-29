# Remote Logout Feature

## Overview
The Remote Logout feature would call an Angel Studios API endpoint to invalidate JWT tokens server-side, providing immediate security benefits beyond local session cleanup.

## Current Implementation Status

### ✅ Completed Features
- **Local Logout**: Clears session cookies, Authorization headers, and cached session data
- **Session Cleanup**: Properly closes HTTP sessions and replaces with fresh session objects
- **User Interface**: Logout option available in addon settings with user notification

### 🔄 Planned Features
- **Remote Token Revocation**: API call to invalidate JWT token server-side when available
- **Immediate Security**: Prevent token reuse even if compromised locally
- **Cross-Device Logout**: Invalidate sessions across all user devices (if supported by Angel Studios)

## Technical Implementation

### Current Local Logout
- **Method**: `logout()` in `AngelStudioSession` class
- **Location**: `resources/lib/angel_authentication.py`
- **Actions**:
  - Clears session cookies via `self.session.cookies.clear()`
  - Removes Authorization header via `self.session.headers.pop("Authorization", None)`
  - Closes HTTP session via `self.session.close()`
  - Clears cached session file
  - Creates fresh session object

### Planned Remote Logout Enhancement
- **API Endpoint**: GraphQL mutation or REST endpoint (when available from Angel Studios)
- **Token Submission**: Send current JWT token for server-side invalidation
- **Fallback**: Graceful degradation to local-only logout if remote endpoint unavailable
- **Error Handling**: Continue with local logout even if remote call fails

## Security Benefits

### Token Revocation
- **Immediate Invalidation**: JWT tokens become unusable immediately upon logout
- **Compromise Mitigation**: Prevents unauthorized use of leaked/cached tokens
- **Session Termination**: Server-side session cleanup prevents further API access

### OAuth 2.0 Compliance
- **Standard Practice**: Follows OAuth 2.0 token revocation best practices
- **Security Hygiene**: Proper token lifecycle management
- **Privacy Protection**: Allows users to properly terminate sessions

## Implementation Requirements

### Angel Studios API
- **Endpoint Availability**: Remote logout endpoint must be exposed by Angel Studios
- **Authentication**: Likely requires valid JWT token for revocation
- **Response**: Confirmation of successful token invalidation

### Code Changes
- **New Method**: `remote_logout()` in authentication classes
- **Integration**: Call remote logout before/after local cleanup
- **Error Handling**: Continue with local logout if remote call fails
- **Testing**: Unit tests for remote logout success/failure scenarios

## User Experience Impact

### Immediate Security
- **Logout Effect**: Takes effect immediately across all systems
- **No Token Reuse**: Prevents accidental or malicious token reuse
- **Clean State**: Server recognizes user has logged out

### Backward Compatibility
- **Graceful Fallback**: Works with local-only logout if remote endpoint unavailable
- **No Breaking Changes**: Existing logout functionality preserved
- **Progressive Enhancement**: Adds security benefits when available

## Status
**Waiting on Angel Studios API**: Implementation blocked until remote logout endpoint is available from Angel Studios. Current local logout provides basic functionality while maintaining security best practices for token storage and session management.