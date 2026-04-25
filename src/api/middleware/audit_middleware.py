"""
AuditMiddleware — auto-logs access to sensitive API routes into audit_logs.

User identity is read off `request.state.user_id` (and `user_aud`), populated
by the auth dependency `_resolve_user_for_audience` in `src/api/dependencies.py`.
The middleware never re-decodes the JWT — that pattern was removed in Phase 1
§1.B.0b (PF.4) because re-decoding without signature verification is a code
smell, even when "safe in practice" because the dep ran first.

Sensitive prefixes audited:
  /api/legal-profile
  /api/contracts
  /api/acts
  /api/ord
"""

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

_SENSITIVE_PREFIXES = (
    "/api/legal-profile",
    "/api/contracts",
    "/api/acts",
    "/api/ord",
)

_METHOD_TO_ACTION = {
    "GET": "READ",
    "POST": "WRITE",
    "PATCH": "WRITE",
    "PUT": "WRITE",
    "DELETE": "DELETE",
}


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

                # PF.4: identity is set by the auth dep on `request.state` —
                # no JWT re-decode here. `getattr(..., None)` is the explicit
                # fallback for routes that somehow run without the dep
                # (shouldn't happen on sensitive prefixes, defensive).
                user_id = getattr(request.state, "user_id", None)
                user_aud = getattr(request.state, "user_aud", None)
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
                        extra={
                            "path": path,
                            "method": request.method,
                            "aud": user_aud,
                        },
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
    if path.startswith("/api/acts"):
        return "act"
    if path.startswith("/api/ord"):
        return "ord"
    return "unknown"
