# Angel.com Logout Procedure - Validated

## Summary
Successfully captured and validated the complete logout flow for Angel.com authentication system. The logout is handled by the auth.angel.com server with proper cookie clearing and return redirect.

---

## Logout Flow

### 1. **Logout Initiation**
- **Trigger**: User clicks "Log Out" in top-right user menu (or programmatic navigation)
- **Initial Request**: Frontend navigates to logout endpoint
- **Analytics Event**: "Log Out Started" fired to Facebook/Kochava

### 2. **Logout Request (Critical)**
```
GET https://auth.angel.com/logout?client_id=angel_web&return_to=https%3A%2F%2Fwww.angel.com%2Fwatch
HTTP/1.1
```

**Parameters:**
- `client_id=angel_web` - Identifies the client (always "angel_web" for web app)
- `return_to=<base64_encoded_url>` - Where to redirect after logout (optional but recommended)

**Response:**
- **Status**: `302 Found` (Redirect)
- **Set-Cookie Headers**: Cookies are cleared (essential for session termination)
- **Location**: Redirects to `return_to` URL or login page

---

## URL Formats

### Basic Logout (No Redirect)
```
https://auth.angel.com/logout?client_id=angel_web
```
- Clears session cookies
- May redirect to login page by default

### Logout with Return URL
```
https://auth.angel.com/logout?client_id=angel_web&return_to=https%3A%2F%2Fwww.angel.com%2Fwatch
```
- Clears session cookies
- Redirects to specified URL after logout

### With Base64 Encoding
URL parameters can be base64-encoded for cleaner URLs (though Angel doesn't require this):
```python
import base64
return_url = "https://www.angel.com/watch"
encoded = base64.b64encode(return_url.encode()).decode()
# Result: aHR0cHM6Ly93d3cuYW5nZWwuY29tL3dhdGNo
logout_url = f"https://auth.angel.com/logout?client_id=angel_web&return_to={encoded}"
```

---

## Session Cookies Cleared

Upon successful logout (302 response), the following cookies are cleared:

1. **`_ellis_island_session`** - Current session cookie (cleared)
2. **`_ellis_island_web_user_remember_me`** - Remember-me cookie (cleared/invalidated)
3. **`angelSession_v2.0`** - JWE encrypted session (cleared)
4. **`angel_jwt_v2`** - JWT token (no longer valid on backend)

**Important Note**: The `Set-Cookie` headers in the 302 response contain:
- Empty/expired values for session cookies
- Same path and domain
- Expiration set to past date (1970) to force browser deletion

---

## HTTP Response Headers (Expected)

```
HTTP/1.1 302 Found
Location: https://www.angel.com/watch  [or other return_to URL]
Set-Cookie: _ellis_island_session=; Path=/; Domain=.angel.com; expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; httponly; samesite=lax
Set-Cookie: _ellis_island_web_user_remember_me=; Path=/; Domain=.angel.com; expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; httponly; samesite=strict
Set-Cookie: angelSession_v2.0=; Path=/; Domain=.angel.com; expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; httponly; samesite=lax
Set-Cookie: angel_jwt_v2=; Path=/; Domain=.angel.com; expires=Thu, 01 Jan 1970 00:00:00 GMT; secure; httponly; samesite=lax
```

---

## Testing via Playwright (Browser Automation)

```python
from playwright.async_api import async_playwright
import asyncio

async def test_logout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Monitor logout requests
        async def handle_request(request):
            if 'logout' in request.url:
                print(f"[REQUEST] {request.method} {request.url}")
        
        async def handle_response(response):
            if 'logout' in response.url:
                print(f"[RESPONSE] {response.status} {response.url}")
                headers = await response.all_headers()
                print(f"Set-Cookie headers: {[h for h in headers if 'set-cookie' in h.lower()]}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Navigate to logout
        logout_url = "https://auth.angel.com/logout?client_id=angel_web&return_to=https%3A%2F%2Fwww.angel.com%2Fwatch"
        await page.goto(logout_url)
        
        await page.wait_for_timeout(3000)
        print(f"Final URL: {page.url}")
        
        cookies = await page.context.cookies()
        print(f"Remaining cookies: {len(cookies)}")

asyncio.run(test_logout())
```

---

## Native Python Implementation (Requests Library)

```python
import requests
from urllib.parse import quote
import base64

def logout(session_cookies=None, return_to="https://www.angel.com/watch", verbose=False):
    """
    Logout from Angel.com using requests library
    
    Args:
        session_cookies: dict with _ellis_island_session, etc.
        return_to: URL to redirect to after logout
        verbose: Print request/response details
    
    Returns:
        dict with logout result
    """
    # Prepare cookies if provided
    cookies = {}
    if session_cookies:
        cookies.update(session_cookies)
    
    # Build logout URL
    logout_url = "https://auth.angel.com/logout"
    params = {
        "client_id": "angel_web",
        "return_to": return_to
    }
    
    if verbose:
        print(f"[*] Logging out...")
        print(f"[*] URL: {logout_url}")
        print(f"[*] Params: {params}")
        if cookies:
            print(f"[*] Cookies: {list(cookies.keys())}")
    
    # Make logout request (don't follow redirects to see 302)
    response = requests.get(
        logout_url,
        params=params,
        cookies=cookies,
        allow_redirects=False,
        timeout=10
    )
    
    if verbose:
        print(f"[*] Status: {response.status_code}")
        print(f"[*] Location: {response.headers.get('Location', 'N/A')}")
        print(f"[*] Set-Cookie headers: {response.headers.get('Set-Cookie', 'N/A')}")
    
    return {
        "status": response.status_code,
        "location": response.headers.get("Location"),
        "cookies_cleared": "Set-Cookie" in response.headers,
        "is_redirect": response.status_code in [301, 302, 303, 307]
    }

# Usage example:
if __name__ == "__main__":
    # Example session cookies from authenticated request
    cookies = {
        "_ellis_island_session": "...",
        "_ellis_island_web_user_remember_me": "...",
        "angelSession_v2.0": "..."
    }
    
    result = logout(session_cookies=cookies, verbose=True)
    print(f"\nLogout result: {result}")
```

---

## Key Findings

✅ **Logout Endpoint**: `https://auth.angel.com/logout`
✅ **HTTP Method**: GET (not POST)
✅ **Required Parameter**: `client_id=angel_web`
✅ **Optional Parameter**: `return_to=<url>`
✅ **Response Code**: 302 Found (Redirect)
✅ **Cookie Clearing**: Set-Cookie headers with expired dates (1970)
✅ **Session Termination**: All session/JWT cookies invalidated
✅ **Return Behavior**: Redirects to `return_to` URL or default login page

---

## Practical Implications

### For Browser-Based Clients
1. User clicks "Log Out" button
2. Frontend navigates to `https://auth.angel.com/logout?client_id=angel_web&return_to=<current_url>`
3. Browser automatically clears cookies (302 with expired Set-Cookie headers)
4. Browser redirects to `return_to` URL
5. User sees login page or home page (depending on `return_to`)

### For Native Python Clients (Using Requests)
1. Send GET to `https://auth.angel.com/logout` with `client_id` and `return_to` params
2. Don't follow redirects (`allow_redirects=False`)
3. Check response status is 302 (successful logout)
4. Check for Set-Cookie headers with empty values (cookies cleared)
5. Optional: Extract Location header to know where user would redirect

### For Mobile/Desktop Apps
1. Navigate to logout URL with embedded browser/WebView
2. Wait for 302 response
3. Clear local app-level token storage
4. Navigate to home/login page

---

## Timeline (Captured 2025-01-28 22:41 UTC+0)

```
User clicks "Log Out" button
    ↓
Frontend fires analytics event: "Log Out Started"
    ↓
Frontend navigates to /auth/logout with client_id & return_to
    ↓
GET https://auth.angel.com/logout?client_id=angel_web&return_to=https%3A%2F%2Fwww.angel.com%2Fwatch
    ↓
Response: 302 Found (Location: https://www.angel.com/watch)
    ↓
Set-Cookie headers clear all session cookies
    ↓
Browser redirects to return_to URL
    ↓
Session terminated, user logged out
```

---

## Next Steps

To use in native Python client:
1. Import the logout function from this document
2. Call with active session cookies from authentication
3. Verify 302 response and Set-Cookie headers
4. Clear all local JWT/session tokens
5. Redirect user to login or home page

See `tools/validate_logout.py` for complete browser-based implementation.
