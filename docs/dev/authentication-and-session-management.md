# Authentication and Session Management

## Overview

This document outlines the authentication and session management architecture for the Kodi Angel Studios plugin. The system uses JWT-based authentication with proactive session validation to ensure all GraphQL API calls are authenticated.

## Architecture

### Components

- **AuthenticationCore**: Handles OAuth flow, token storage/retrieval, and session validation
- **SessionStore**: Abstract base class for pluggable storage (currently KodiSessionStore)
- **AngelStudiosInterface**: KODI-agnostic API client with proactive session validation
- **Kodi UI Interface**: Handles user interaction and error presentation

### Session Validation Strategy

**Proactive Validation**: Before each GraphQL request, validate the session and refresh if needed. This prevents failed API calls and improves UX by failing fast.

**Reactive Fallback**: If validation succeeds but API returns auth errors, raise AuthenticationRequiredError for UI handling.

## Workflow

### GraphQL Request Flow

1. Method calls `_graphql_query(operation, variables)`
2. **Proactive Check**: `auth_core.validate_session()` 
   - If invalid/expiring: Attempt refresh via `auth_core.ensure_valid_session()`
   - If refresh fails: Raise `AuthenticationRequiredError`
   - If refresh succeeds: Update session headers, continue
3. Execute GraphQL request
4. **Reactive Check**: If API returns auth errors, raise `AuthenticationRequiredError`
5. Return data or handle other errors

### Authentication States

- **Valid**: Proceed with request
- **Expiring**: Refresh token automatically
- **Expired/Invalid**: Raise exception for UI to handle (prompt login)
- **Refresh Failed**: Raise exception (user needs to re-auth manually)

## Implementation Details

### AuthenticationCore Methods

- `validate_session()`: Check token validity (local decode, expiry check)
- `ensure_valid_session()`: Check and refresh token if expiring/expired, return success/failure
- `authenticate()`: Full OAuth flow for initial login
- `logout()`: Clear stored tokens

### SessionStore Interface

- `get_token()`: Retrieve stored JWT
- `set_token(token)`: Store JWT
- `clear()`: Remove stored token

### Error Handling

- `AuthenticationRequiredError`: Raised when auth is needed
- `SessionExpiredError`: Token is expired
- `InvalidCredentialsError`: Login credentials invalid

## Considerations

### Refactoring get_projects_by_slugs

The `get_projects_by_slugs` method currently implements its own GraphQL request logic instead of using `_graphql_query`. This bypasses proactive validation.

**Options**:
1. Refactor `get_projects_by_slugs` to use `_graphql_query` (recommended)
2. Extract common auth helper method for both `_graphql_query` and `get_projects_by_slugs`

### Reauth Failure Handling

Reauth failures should always raise `AuthenticationRequiredError` to ensure the UI prompts for login. No silent failures.

### Expiry Buffer

The expiry buffer is configurable via Kodi settings (default: 1 hour). This determines when to trigger automatic refresh before JWT expiration.

### Concurrency Handling

Due to Kodi's single-threaded nature, race conditions during refresh are unlikely. Concurrency handling is skipped for now as an edge case.

## Testing

- Mock `validate_session()` to return various states
- Test refresh success/failure paths
- Verify UI receives `AuthenticationRequiredError` appropriately
- Ensure 100% test coverage

## Future Enhancements

- Token refresh buffer configuration
- Background refresh for long sessions
- Multi-device session management
