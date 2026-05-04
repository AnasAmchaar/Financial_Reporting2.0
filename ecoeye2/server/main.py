"""
EcoEye2 FastAPI entrypoint.

Load `.env` from project root before importing `config` so ECOEYE2_* paths apply.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ecoeye2.server.routes import api_router

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

app = FastAPI(title="EcoEye2", version="2.0.0", description="Financial ETL, adjustments, and visualization")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Production assets (Vite build -> static/assets)
_assets = STATIC_DIR / "assets"
if _assets.is_dir():
    app.mount("/assets", StaticFiles(directory=_assets), name="assets")


@app.get("/favicon.ico")
def favicon():
    ico = STATIC_DIR / "favicon.ico"
    if ico.is_file():
        return FileResponse(ico)
    from fastapi.responses import Response

    return Response(status_code=204)


@app.get("/")
def root_index():
    if INDEX_HTML.is_file():
        return FileResponse(INDEX_HTML)
    return {
        "app": "EcoEye2",
        "message": "API is running. Build the SPA: cd ecoeye2/web && npm run build",
        "docs": "/docs",
    }


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    from fastapi import HTTPException

    if full_path.startswith("api") or full_path.startswith("assets"):
        raise HTTPException(status_code=404)
    if INDEX_HTML.is_file():
        return FileResponse(INDEX_HTML)
    raise HTTPException(status_code=404)
