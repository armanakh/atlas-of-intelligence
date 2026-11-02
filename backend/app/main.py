"""FastAPI application factory for the local curriculum API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from app.api.errors import install_error_handlers
from app.api.routes.curriculum import router as curriculum_router
from app.api.routes.dependencies import router as dependencies_router
from app.api.routes.learners import router as learners_router
from app.api.routes.learner_progress import router as progress_router
from app.db.database import make_engine, make_session_factory


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    owned_engine = None
    if session_factory is None:
        owned_engine = engine or make_engine()
        session_factory = make_session_factory(owned_engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        if owned_engine is not None and engine is None:
            owned_engine.dispose()

    app = FastAPI(title="First-Principles AI Curriculum Explorer API", version="1.0.0", lifespan=lifespan)
    app.state.session_factory = session_factory
    install_error_handlers(app)
    origins = [
        origin.strip()
        for origin in os.environ.get(
            "API_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(curriculum_router)
    app.include_router(dependencies_router)
    app.include_router(learners_router)
    app.include_router(progress_router)
    return app


app = create_app()
