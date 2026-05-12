import httpx


async def extract_bearer_from_headers(headers: dict) -> str | None:
    """Extract Bearer token from Authorization header (case-insensitive)."""
    headers_lower = {k.lower(): v for k, v in headers.items()}
    auth = headers_lower.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth  # return full "Bearer <token>" string
    return None


async def extract_token_from_cookie(
    headers: dict, accounts_url: str
) -> str | None:
    """Exchange a session cookie for a Bearer token via whoami endpoint."""
    headers_lower = {k.lower(): v for k, v in headers.items()}
    cookie = headers_lower.get("cookie", "")
    if not cookie:
        return None

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{accounts_url}/auth/sessions/whoami",
                headers={
                    "Accept": "application/json",
                    "Cookie": cookie,
                },
                params={"tokenize_as": "jwt_template"},
            )
            resp.raise_for_status()
            data = resp.json()
            tokenized = data.get("tokenized")
            if tokenized:
                return f"Bearer {tokenized}"
        except httpx.HTTPError:
            pass
    return None
