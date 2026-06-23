from http.cookies import SimpleCookie


def extract_bearer_from_headers(headers: dict) -> str | None:
    """Extract Bearer token from Authorization header (case-insensitive)."""
    headers_lower = {k.lower(): v for k, v in headers.items()}
    auth = headers_lower.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth  # return full "Bearer <token>" string
    return None


def extract_session_cookie(headers: dict) -> str | None:
    """Return only the Connhex session value from an incoming Cookie header."""
    headers_lower = {k.lower(): v for k, v in headers.items()}
    raw_cookie = headers_lower.get("cookie")
    if not raw_cookie:
        return None
    cookie = SimpleCookie()
    cookie.load(raw_cookie)
    morsel = cookie.get("chx_auth_session")
    return morsel.value if morsel else None
