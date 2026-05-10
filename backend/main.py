"""FastAPI entrypoint. Mounts routers and serves the built frontend."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import load_settings
from routers import candidate as candidate_router
from routers import manager as manager_router

app = FastAPI(title="VA Interview Test")

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
