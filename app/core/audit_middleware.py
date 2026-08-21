import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.activity_log import ActivityLog

EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        if request.url.path in EXCLUDED_PATHS:
            return response

        analyst_id = self._extract_analyst_id(request)

        db = SessionLocal()
        try:
            db.add(ActivityLog(
                analyst_id=analyst_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip_address=request.client.host if request.client else None,
                duration_ms=duration_ms,
            ))
            db.commit()
        except Exception as e:
            print(f"[audit] failed to log request: {e}")
            db.rollback()
        finally:
            db.close()

        return response

    def _extract_analyst_id(self, request: Request) -> int | None:
        """
        Independent JWT decode, not reliant on the route's own
        get_current_user dependency — middleware runs outside that
        dependency-injection lifecycle, so it needs its own lightweight
        decode. Failure here just means an anonymous log entry, not an error.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            return int(payload.get("sub"))
        except Exception:
            return None