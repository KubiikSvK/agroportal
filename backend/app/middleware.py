from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings

class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, protected_prefixes=None):
        super().__init__(app)
        self.protected_prefixes = protected_prefixes or []

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.protected_prefixes):
            if not settings.api_key:
                return await call_next(request)
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != settings.api_key:
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
        return await call_next(request)
