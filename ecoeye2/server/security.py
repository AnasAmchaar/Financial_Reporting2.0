"""Optional API key gate (set ECOEYE2_API_KEY in environment)."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")) -> None:
    expected = os.environ.get("ECOEYE2_API_KEY", "").strip()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key")
