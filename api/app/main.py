from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, projects, provider_configs, setup
from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory


def create_app(*, session_factory=None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Persona API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if session_factory is None:
        engine = create_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        app.state.engine = engine
    app.state.session_factory = session_factory

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(setup.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(provider_configs.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")

    return app


app = create_app()

