# JWT Re-issuance & Session Management Mechanism

## Quick Answer

**No, there is no separate refresh token endpoint.** The JWT re-issuance works through a **hybrid session-cookie fallback mechanism**:

- **JWT**: 24-hour expiration, used for stateless API requests
- **Session Cookies**: ~24-hour expiration (same as JWT), used as fallback
- **Remember-me Cookie**: Long-lived, persists across JWT expiry
- **Re-issuance**: LAZY (not automatic) - only on re-login or explicit refresh

---

## Token Lifetimes

```
angel_jwt_v2                     Expires in ~24 hours
                                 - Symmetric signature (HS512)
                                 - Claims: user_id, scope, email
                                 - Used in Authorization: Bearer header

angelSession_v2.0               Expires in ~24 hours  
(Encrypted JWE, A256GCM)        - Contains full session state
                                 - DIR key agreement (symmetric encryption)
                                 - Stores user_id + app data

_ellis_island_session           Expires with JWT
(JWE Encrypted)                 - Current session state
                                 - Phoenix LiveView session

_ellis_island_web_user_remember_me  PERSISTENT (~180 days)
(Erlang Binary Format)          - Long-lived persistent token
                                 - Survives JWT expiration
                                 - SOURCE OF TRUTH for re-authentication
```

---

## How Re-issuance Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Ellis Island (Phoenix Auth Server)                 │
│ https://www.angel.com                              │
│                                                     │
│ Responsible for:                                   │
│ - Session creation (/u/login/password)           │
│ - OAuth callbacks (/api/auth/callback)           │
│ - Session validation                              │
│ - Cookie encryption/decryption                    │
└─────────────────────────────────────────────────────┘
           ↓ (sets cookies)
┌─────────────────────────────────────────────────────┐
│ GraphQL API (api.angelstudios.com)                │
│                                                     │
│ Middleware Stack:                                  │
│ 1. guardian.on_authenticated         → JWT auth    │
│ 2. absinthe_context_plugin           → Setup ctx  │
│ 3. Session cookie fallback           → If JWT bad │
│                                                     │
│ Authorization priority:                            │
│ 1. JWT in Authorization header      (fast)        │
│ 2. Session cookies                  (fallback)    │
└─────────────────────────────────────────────────────┘
```

### Step-by-Step Request Flow

#### Scenario 1: Valid JWT (Normal case)

```
Client:
  Authorization: Bearer <valid_jwt>
  Cookies: [...session cookies...]

Server (GraphQL API):
  ✓ Validate JWT signature
  ✓ Check expiration (not expired)
  ✓ Extract user_id from claims
  ✓ Execute query
  
Response:
  200 OK + query results
  Set-Cookie: __cf_bm (Cloudflare only, no JWT update)
```

#### Scenario 2: Expired JWT + Valid Session Cookies

```
Client:
  Authorization: Bearer <expired_jwt>
  Cookies: [
    _ellis_island_web_user_remember_me: <valid>,
    _ellis_island_session: <valid>,
    angelSession_v2.0: <valid>
  ]

Server (GraphQL API):
  ✗ JWT validation fails (expired)
  ↓
  Phoenix :wrap_session middleware kicks in
  Looks at session cookies in conn.private
  ✓ Validates _ellis_island_web_user_remember_me
  ✓ Decrypts session state
  ✓ Extracts user_id from session
  ✓ User authenticated via session cookies
  ✓ Execute query with session-based auth
  
Response:
  200 OK + query results
  Set-Cookie: __cf_bm (Cloudflare only, no JWT issued)
  
Client:
  Still has expired JWT in local storage/cookies
  Next request will also fail JWT validation
  But session cookies still valid for ~24h
```

#### Scenario 3: Missing JWT + Valid Session Cookies

```
Client:
  [No Authorization header]
  Cookies: [...session cookies...]

Server (GraphQL API):
  No Authorization header → Skip JWT auth
  ↓
  Check session cookies
  ✓ Session validated
  ✓ Query executes with session auth
  
Response:
  200 OK + results
  
Note: This works! Session cookies alone are sufficient.
```

---

## Key Findings

### 1. **No Active JWT Re-issuance**

The API does NOT automatically re-issue JWT tokens in responses. The JWT is only issued once during the login flow:

```
POST /u/login/password (email+password+state)
↓
Session created (cookies set)
↓
Redirect to /api/auth/callback?code=XXX
↓
JWT issued (Set-Cookie: angel_jwt_v2)
↓
Redirect to /watch
```

### 2. **Session Cookies Provide Fallback**

When JWT expires:
- Client continues using expired JWT (no validation failure)
- Server validates JWT, sees it's expired
- Falls back to session cookie validation
- Request succeeds with session auth
- No new JWT issued in response

### 3. **No Separate Refresh Token**

Unlike traditional OAuth2 patterns, Angel doesn't have:
- ❌ `/api/refresh-token` endpoint
- ❌ Refresh token in response
- ❌ Automatic JWT re-issuance on every request

Instead:
- ✅ Session cookies act as implicit refresh mechanism
- ✅ Lazy re-issuance (only on re-login)
- ✅ Seamless experience: session outlives JWT

### 4. **The Remember-me Cookie is the Master Token**

`_ellis_island_web_user_remember_me` is the persistent token:
- Encrypted with Erlang Binary Format
- Used by Phoenix to validate and recreate sessions
- Survives beyond JWT expiration
- Is the source of truth when JWT invalid

---

## Session Duration Strategy

```
Timeline:
─────────────────────────────────────────────────
T=0h:   User logs in
        JWT: exp=+24h    ✓
        Session: exp=+24h ✓
        Remember-me: exp=+180d ✓

T=12h:  Request with valid JWT
        JWT auth: ✓ (used)
        Session cookies: ✓ (not checked)

T=24h:  JWT expires, but user makes another request
        JWT auth: ✗ (expired, skipped)
        Session auth: ✓ (still valid, used)
        Remember-me: ✓ (still valid)
        
T=25h:  Another request
        JWT: ✗ (still expired)
        Session: ✗ (also expired now)
        Remember-me: ✓ (still valid!)
        
        Server can issue NEW JWT using remember-me
        But currently doesn't (lazy approach)
        User redirected to login on UI refresh

T=180d: Remember-me expires
        Session completely lost
        User must log in again
```

---

## Practical Implications for Native Python Client

For `tools/requests_only_scraper.py`:

### Cookies to Persist
```python
cookies_to_keep = {
    'angel_jwt_v2': '<expires in 24h>',
    '_ellis_island_session': '<expires in 24h>',
    '_ellis_island_web_user_remember_me': '<expires in 180d>',
    'angelSession_v2.0': '<expires in 24h>',
}
```

### Request Strategy
```python
# Option 1: Use JWT (preferred for 24h)
headers = {
    'Authorization': f'Bearer {jwt_token}'
}
response = requests.post('https://api.angelstudios.com/graphql', headers=headers)

# Option 2: If JWT expired, omit it and rely on cookies
response = requests.post(
    'https://api.angelstudios.com/graphql',
    cookies=session_cookies  # JWT falls back to session auth
)
```

### Refresh Strategy
```python
# There is NO refresh endpoint!
# Options:
# 1. Re-run login flow: tools/complete_auth.py (gets new JWT + cookies)
# 2. Rely on session cookies: Works for ~24h after JWT expires
# 3. Implement scheduled re-login: Run complete_auth.py every 12h
```

---

## See Also

- `complete_auth_data.json`: Current session with all cookies + JWT
- `tools/complete_auth.py`: Playwright-based login (issues new JWT)
- `auth_login_page.html`: Login page form structure (state parameter)
- `tools/investigate_auth_state.py`: Auth state investigation

---

## Conclusion

**JWT re-issuance is NOT automatic**. The system uses a clever hybrid approach:

1. **JWT** for fast, stateless API validation (24h)
2. **Session cookies** as fallback (24h + remember-me up to 180d)
3. **No refresh token** - just re-authenticate via login flow
4. **Lazy re-issuance** - only happens on explicit user login

This design keeps the API simple while providing persistence through session cookies.
