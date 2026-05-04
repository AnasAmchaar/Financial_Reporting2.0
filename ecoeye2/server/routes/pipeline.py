"""ETL and econ pipeline triggers."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from etl.pipeline import run_etl_all, run_etl_for_file, run_etl_single
from econ.apply import apply_all
from econ.fetcher import fetch_all, load_econ_indicators_to_sqlite

from ecoeye2.server.deps import pipeline_lock
router = APIRouter()


class EtlBody(BaseModel):
    filename: str | None = None
    mode: Literal["all", "file", "tables"] = "all"
    tables: list[str] = Field(default_factory=list)


def _serialize_tables(results):
    return [{"table": x.table, "ok": x.ok, "rows": x.rows, "error": x.error} for x in results]


@router.post("/pipeline/etl")
async def run_etl(body: EtlBody):
    async with pipeline_lock:
        if body.mode == "tables":
            if not body.tables:
                raise HTTPException(400, "tables required for mode=tables")
            agg: list = []
            ok = True
            for t in body.tables:
                tr = run_etl_single(t)
                agg.extend(tr.tables)
                if not tr.ok:
                    ok = False
            return {"ok": ok, "message": None, "tables": _serialize_tables(agg)}

        if body.mode == "all":
            r = run_etl_all()
        elif body.mode == "file":
            if not body.filename:
                raise HTTPException(400, "filename required for mode=file")
            r = run_etl_for_file(body.filename, table_names=body.tables or None)
        else:
            raise HTTPException(400, "invalid mode")

    return {"ok": r.ok, "message": r.message, "tables": _serialize_tables(r.tables)}


@router.post("/pipeline/econ/fetch")
async def econ_fetch(source: str | None = None):
    async with pipeline_lock:
        df = fetch_all(source_filter=source)
        load_econ_indicators_to_sqlite(df)
    return {"ok": True, "rows": len(df)}


@router.post("/pipeline/econ/apply")
async def econ_apply():
    async with pipeline_lock:
        apply_all()
    return {"ok": True}
