# Feature: Angel Auth Token Refresh

**Date:** January 21, 2026
**Status:** ❌ OBSOLETED
**Owner:** Architecture & Product
**Audience:** Developer
**Obsoleted By:** feature-refactor-authentication-module.md (2026-01-28)
**Reason:** Superseded by comprehensive authentication refactor that implemented proactive session validation with automatic token refresh using stored credentials.

---

## Executive Summary

❌ **OBSOLETED**: This feature was planned to implement automatic session refresh using refresh tokens, but was superseded by the comprehensive authentication module refactor which implemented a superior solution.

### Original Scope (No Longer Applicable)
- Investigate Angel Studios refresh token API support
- Implement refresh token storage and management
- Modify session validation to attempt refresh before full re-auth
- Add refresh token expiry handling

### Why Obsoleted
The authentication refactor implemented a more robust solution:
- ✅ **Proactive session validation** before every GraphQL request
- ✅ **Automatic token refresh** using stored credentials (no refresh tokens needed)
- ✅ **Configurable expiry buffer** (default 1 hour before expiry)
- ✅ **Seamless user experience** without login interruptions
- ✅ **Clean architecture** with proper separation of concerns

**Risk Profile:** N/A (superseded)

**Timeline Estimate:** 6-8 hours

**Success Criteria:**
1. Refresh tokens supported and working with Angel API
2. Automatic token refresh before expiry
3. Seamless user experience without login interruptions
4. Secure refresh token storage
5. Backward compatibility maintained

---

## Current State Assessment

### Authentication Flow
- JWT access tokens expire after ~1 hour
- Current validation only checks expiry
- Full re-auth required when tokens expire
- Session persistence works via pickle

### Issues
- Users get logged out during long viewing sessions
- Manual re-authentication required
- Poor UX for extended usage

---

## Investigation Required

### Angel Studios API Analysis

**Questions to Answer:**
1. Does Angel Studios OAuth support refresh tokens?
2. What is the refresh token endpoint and format?
3. How long do refresh tokens last?
4. What is returned in refresh responses?

**Investigation Method:**
- Run login flows through test harness
- Capture network traffic during authentication
- Analyze JWT token payloads for refresh hints
- Test with extended sessions to see token behavior

---

## Implementation Plan

### 1. API Investigation
**Action:**
1. Set up test harness to capture auth flows
2. Analyze login responses for refresh token data
3. Test token expiry behavior
4. Document API endpoints and formats

### 2. Refresh Token Storage
**Action:**
1. Add refresh token fields to session persistence
2. Implement secure storage (consider encryption)
3. Add refresh token expiry tracking
4. Update session loading/saving logic

### 3. Refresh Logic Implementation
**Action:**
1. Create `_refresh_session()` method
2. Modify `_validate_session()` to attempt refresh first
3. Handle refresh failures gracefully
4. Add proper error handling and logging

### 4. Testing & Validation
**Action:**
1. Test refresh scenarios (success/failure/expiry)
2. Validate backward compatibility
3. Test extended session behavior
4. Ensure no breaking changes

---

## Technical Details

### Refresh Token Flow
```
Current: Access Token Expired → Full Re-auth
Proposed: Access Token Expired → Refresh Attempt → Full Re-auth (if refresh fails)
```

### Storage Requirements
- Refresh token value
- Refresh token expiry timestamp
- Secure persistence (encrypted if sensitive)

### Error Handling
- Network failures during refresh
- Invalid/expired refresh tokens
- API changes breaking refresh flow
- Graceful fallback to full re-auth

---

## Acceptance Criteria

- [ ] Angel API refresh token support confirmed
- [ ] Refresh tokens stored securely
- [ ] Automatic refresh before access token expiry
- [ ] Seamless user experience maintained
- [ ] Backward compatibility preserved
- [ ] Comprehensive error handling

---

## File Changes

- **Modified:** `resources/lib/angel_authentication.py`
  - Add refresh token storage
  - Implement `_refresh_session()` method
  - Modify `_validate_session()` logic
- **New:** Test cases for refresh scenarios
- **Modified:** Session persistence format

---

## Progress Tracking

- [ ] Investigate Angel API refresh token support
- [ ] Document API endpoints and behavior
- [ ] Implement refresh token storage
- [ ] Add refresh logic to validation
- [ ] Test refresh scenarios
- [ ] Validate user experience improvements

---

## Risk Mitigation

**Risk:** Angel API doesn't support refresh tokens
**Mitigation:** Investigation phase will confirm feasibility before implementation

**Risk:** Refresh implementation breaks existing auth
**Mitigation:** Maintain fallback to full re-auth; extensive testing

**Risk:** Security issues with refresh token storage
**Mitigation:** Use secure storage methods; consider encryption

---

## Dependencies

- Requires investigation of Angel Studios OAuth implementation
- May need API documentation or reverse engineering
- Depends on current session persistence working correctly