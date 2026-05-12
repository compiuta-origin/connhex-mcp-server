from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class OriginValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origin: str):
        super().__init__(app)
        parsed = urlparse(allowed_origin)
        self._allowed = f"{parsed.scheme}://{parsed.netloc}"

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        if origin and origin != self._allowed:
            return Response("Forbidden", status_code=403)
        return await call_next(request)
