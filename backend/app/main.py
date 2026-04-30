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

from app.api import admin, auth, chat, eval as eval_api, healthz, history, memory as memory_api, trace
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
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory_api.router)
app.include_router(history.router)
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

    @app.get("/{full_path:path}")
    async def spa_catchall(full_path: str):
        """Serve Next.js static-exported pages for any non-API path.
        Resolves <full_path>/index.html, then <full_path>.html, then root.
        Strips traversal attempts and hides files outside STATIC_DIR.
        Registered LAST so /api/*, /healthz, /_next/* take precedence."""
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="not found")
        candidates = [
            STATIC_DIR / full_path / "index.html",
            STATIC_DIR / f"{full_path}.html",
            STATIC_DIR / full_path,
        ]
        for p in candidates:
            try:
                p_resolved = p.resolve()
                if p_resolved.is_file() and STATIC_DIR.resolve() in p_resolved.parents:
                    return FileResponse(p_resolved)
            except (OSError, ValueError):
                continue
        return FileResponse(STATIC_DIR / "index.html")
