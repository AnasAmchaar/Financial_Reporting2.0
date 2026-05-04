"""Multipart upload to data/raw."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from config.settings import DATA_RAW_DIR
router = APIRouter()

_SAFE = re.compile(r"[^A-Za-z0-9._\- ]+")


@router.post("/uploads")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    base = _SAFE.sub("_", Path(file.filename).name)
    if not base.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx or .xls files are accepted")
    stem = Path(base).stem
    suffix = Path(base).suffix
    unique = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_RAW_DIR / unique
    content = await file.read()
    if len(content) > 80 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 80 MB)")
    dest.write_bytes(content)
    return {"filename": unique, "path": str(dest), "bytes": len(content)}
