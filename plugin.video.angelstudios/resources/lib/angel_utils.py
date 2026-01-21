"""angel_utils.py
Utility functions shared across Angel Studios modules.
"""

def sanitize_headers_for_logging(headers):
    """Sanitize headers for logging by redacting sensitive information."""
    safe_headers = {}
    for key, val in headers.items():
        key_lower = str(key).lower()
        if key_lower in ("authorization", "cookie", "x-api-key"):
            safe_headers[key] = "[REDACTED]"
        else:
            safe_headers[key] = val
    return safe_headers