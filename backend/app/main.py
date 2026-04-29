"""FastAPI entrypoint. Mounts the static Next.js export at / and registers all API routes."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pythonjsonlogger import jsonlogger

from app.api import admin, chat, eval as eval_api, healthz, memory as memory_api, trace
from app.config import get_settings
from app.db.bootstrap import bootstrap
from app.db.connection import close_pool

STATIC_DIR = Path(__file__).parent.parent / "static"


def _configure_logging(level: str) -> None:
    h = logging.StreamHandler()
    h.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            timestamp=True,
        )
    )
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    _configure_logging(s.log_level)
    log = logging.getLogger("trustflow.startup")
    log.info("starting; running schema bootstrap")
    await bootstrap()
    log.info("bootstrap complete; ready to serve")
    yield
    await close_pool()


app = FastAPI(title="TrustFlow AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthz.router)
app.include_router(chat.router)
app.include_router(memory_api.router)
app.include_router(trace.router)
app.include_router(eval_api.router)
app.include_router(admin.router)

if STATIC_DIR.exists():
    next_static = STATIC_DIR / "_next"
    if next_static.exists():
        app.mount("/_next", StaticFiles(directory=next_static), name="next-static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/eval")
    async def eval_page():
        path = STATIC_DIR / "eval" / "index.html"
        if path.exists():
            return FileResponse(path)
        return FileResponse(STATIC_DIR / "index.html")
