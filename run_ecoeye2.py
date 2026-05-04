"""
Run EcoEye2 (FastAPI + optional built-in SPA).

  python run_ecoeye2.py

Set ECOEYE2_DB_PATH / ECOEYE2_RAW_DIR if needed. Build UI: cd ecoeye2/web && npm run build
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecoeye2.server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
