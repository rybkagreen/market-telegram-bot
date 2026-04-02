"""
AuditMiddleware — auto-logs access to sensitive API routes into audit_logs.

Sensitive prefixes audited:
  /api/legal-profile
  /api/contracts
  /api/ord
"""

import logging
from base64 import b64decode
from json import loads as json_loads

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

_SENSITIVE_PREFIXES = (
    "/api/legal-profile",
    "/api/contracts",
    "/api/ord",
)

_METHOD_TO_ACTION = {
    "GET": "READ",
    "POST": "WRITE",
    "PATCH": "WRITE",
    "PUT": "WRITE",
    "DELETE": "DELETE",
}


def _extract_user_id_from_token(authorization: str | None) -> int | None:
    """Decode JWT payload to get user_id without verifying signature."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1]
        # Add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json_loads(b64decode(payload_b64).decode())
        uid = payload.get("sub") or payload.get("user_id")
        return int(uid) if uid is not None else None
    except Exception:
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    """Log access to sensitive routes after successful responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        is_sensitive = any(path.startswith(prefix) for prefix in _SENSITIVE_PREFIXES)

        response = await call_next(request)

        if is_sensitive and response.status_code < 400:
            try:
                from src.db.repositories.audit_log_repo import AuditLogRepo
                from src.db.session import async_session_factory

                user_id = _extract_user_id_from_token(request.headers.get("Authorization"))
                action = _METHOD_TO_ACTION.get(request.method, "READ")
                ip = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")

                async with async_session_factory() as session:
                    repo = AuditLogRepo(session)
                    await repo.log(
                        action=action,
                        resource_type=_path_to_resource_type(path),
                        user_id=user_id,
                        target_user_id=user_id,
                        ip_address=ip,
                        user_agent=user_agent,
                        extra={"path": path, "method": request.method},
                    )
                    await session.commit()
            except Exception:
                logger.warning("AuditMiddleware: failed to write audit log", exc_info=True)

        return response


def _path_to_resource_type(path: str) -> str:
    if path.startswith("/api/legal-profile"):
        return "legal_profile"
    if path.startswith("/api/contracts"):
        return "contract"
    if path.startswith("/api/ord"):
        return "ord"
    return "unknown"
