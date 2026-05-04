"""Shared FastAPI dependencies and job serialization (SQLite single-writer)."""

from __future__ import annotations

import asyncio

# Serialize ETL and econ jobs to avoid SQLite write races
pipeline_lock = asyncio.Lock()
