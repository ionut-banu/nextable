"""The FastAPI application: routers, error shape, nothing else.

Routers validate and delegate; services own the rules (AGENTS.md).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect
from fastapi.middleware.cors import CORSMiddleware

from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.api import auth, config, parties, stats, waitlist
from app.auth import LoginRateLimiter
from app.config import get_settings
from app.db import get_engine
from app.services.errors import IllegalTransition, PartyNotFound

DESCRIPTION = "Walk-in waitlist for one restaurant: a host console and a guest status page."


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Fail loudly at boot rather than with "no such table" on the first request."""
    if not inspect(get_engine()).has_table("parties"):
        raise RuntimeError(
            "The database has no schema. Run `uv run alembic upgrade head` first."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Nextable",
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.login_limiter = LoginRateLimiter(
        limit=settings.login_attempt_limit,
        window_seconds=settings.login_attempt_window_seconds,
    )

    # The frontend dev server is a different origin and must send the session
    # cookie, so the allowed origins are explicit rather than a wildcard.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain errors become status codes here, and nowhere else. Every error
    # body is {"detail": "..."} (spec 12).
    @app.exception_handler(PartyNotFound)
    def _party_not_found(_: Request, error: PartyNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(IllegalTransition)
    def _illegal_transition(_: Request, error: IllegalTransition) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    app.include_router(auth.router)
    app.include_router(parties.router)
    app.include_router(waitlist.router)
    app.include_router(stats.router)
    app.include_router(config.router)
    return app


app = create_app()
