"""API routers package.

Use explicit submodule imports rather than re-exports here, e.g.::

    from src.api.routers.auth import router as auth_router

Rationale: re-exporting via ``from .auth import router as auth`` shadows
the submodule path ``src.api.routers.auth`` (the name resolves к APIRouter
object, не к module), which breaks ``importlib.import_module`` lookups
и ``monkeypatch.setattr`` patterns в тестах. (BL-067 cleanup, 2026-05-01.)
"""
