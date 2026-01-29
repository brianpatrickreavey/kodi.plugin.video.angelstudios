# Remote Logout Feature

## Overview
The Remote Logout feature would call an Angel Studios API endpoint to invalidate JWT tokens server-side, providing immediate security benefits beyond local session cleanup. Technical details documented in LOGOUT_PROCEDURE.md.

## Current Implementation Status

### ✅ Completed Features
- **Local Logout**: Clears session cookies, Authorization headers, and cached session data
- **Session Cleanup**: Properly closes HTTP sessions and replaces with fresh session objects
- **User Interface**: Logout option available in addon settings with user notification

### 🔄 Planned Features
- **Remote Token Revocation**: API call to invalidate JWT token server-side using Angel Studios logout endpoint
- **Immediate Security**: Prevent token reuse even if compromised locally
- **Cross-Device Logout**: Invalidate sessions across all user devices via server-side session termination

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
- **API Endpoint**: `https://auth.angel.com/logout`
- **HTTP Method**: GET request
- **Required Parameters**:
  - `client_id=angel_web`
  - `return_to=<optional_redirect_url>`
- **Response**: `302 Found` redirect with `Set-Cookie` headers that clear all session cookies
- **Cookies Cleared**: `_ellis_island_session`, `_ellis_island_web_user_remember_me`, `angelSession_v2.0`, `angel_jwt_v2`
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
- **Endpoint Available**: `https://auth.angel.com/logout` (documented in LOGOUT_PROCEDURE.md)
- **Authentication**: Uses current session cookies (no additional auth required)
- **Response Validation**: Check for 302 status and Set-Cookie headers with expired dates
- **Cookie Clearing**: Server automatically clears all session/JWT cookies via Set-Cookie headers

### Code Changes
- **New Method**: `remote_logout()` in `AngelStudioSession` class
- **Integration**: Call remote logout before local cleanup to ensure server-side invalidation
- **HTTP Request**: GET request with `client_id=angel_web` parameter
- **Response Handling**: Don't follow redirects (`allow_redirects=False`) to inspect 302 response
- **Error Handling**: Continue with local logout if remote call fails or times out
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
**Ready for Implementation**: Angel Studios logout endpoint is available and documented in LOGOUT_PROCEDURE.md. Implementation involves adding remote logout call to existing `logout()` method with proper error handling and fallback to local-only logout.