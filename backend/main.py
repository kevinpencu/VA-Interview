"""FastAPI entrypoint. Mounts routers and serves the built frontend."""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import load_settings
from routers import candidate as candidate_router
from routers import manager as manager_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("va-interview")

app = FastAPI(title="VA Interview Test")


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception):
    """Log unhandled exceptions so they appear in Railway logs (visible & searchable)
    instead of a bare 'Internal Server Error' from FastAPI's default handler."""
    log.error(
        "Unhandled %s on %s %s: %s\n%s",
        type(exc).__name__, request.method, request.url.path, exc,
        traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# CORS — origins configured via CORS_ORIGINS env (comma-separated)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(load_settings().cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


app.include_router(candidate_router.router)
app.include_router(manager_router.router)


# Static frontend (built into ../frontend/dist by Dockerfile / npm run build)
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        # SPA fallback: any non-API path returns index.html.
        # Explicitly 404 /api/ so future routers can't be shadowed by mount order.
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(FRONTEND_DIST / "index.html")
