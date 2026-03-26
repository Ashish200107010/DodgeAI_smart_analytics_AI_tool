from __future__ import annotations

from fastapi import FastAPI

from app.api.routers.chat import router as chat_router
from app.api.routers.domain import router as domain_router
from app.api.routers.graph import router as graph_router
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="DodgeAI Backend",
        version="0.1.0",
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(domain_router)
    app.include_router(graph_router)
    app.include_router(chat_router)

    return app


app = create_app()

