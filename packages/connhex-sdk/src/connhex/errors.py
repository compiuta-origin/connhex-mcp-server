import httpx


class ConnhexAPIError(Exception):
    """Structured error from a Connhex API response."""

    def __init__(self, status: int, detail: str, errors: list | None = None):
        self.status = status
        self.detail = detail
        self.errors = errors or []
        super().__init__(f"Connhex API error {status}: {detail}")


def raise_for_connhex_response(resp: httpx.Response) -> None:
    """Convert HTTP error responses to structured ConnhexAPIError."""
    if resp.is_success:
        return

    try:
        body = resp.json()
        # JSON:API error format
        errors = body.get("errors", [])
        if errors:
            detail = errors[0].get("detail", resp.reason_phrase)
        else:
            # Ory/non-JSON:API error format
            detail = body.get("error", {}).get("message", resp.reason_phrase)
    except Exception:
        detail = resp.text[:500] if resp.text else resp.reason_phrase
        errors = []

    raise ConnhexAPIError(resp.status_code, detail, errors)
