"""
RAG Indexer for EcoEye2.

Reads every relevant table from the SQLite database, generates
natural-language summary chunks (monthly aggregates, per-dimension
breakdowns, economic indicator narratives, derived metrics), embeds
them with Google Gemini's gemini-embedding-001 model, and stores them
in a persistent ChromaDB collection.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import DB_PATH, PROJECT_ROOT

logger = logging.getLogger(__name__)

CHROMA_DIR = PROJECT_ROOT / "db" / "chroma"
COLLECTION_NAME = "ecoeye2_financial"

# ---------------------------------------------------------------------------
# Embedding helper (Gemini gemini-embedding-001)
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 3072

def _embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed a list of texts using the Gemini embedding model.

    Retries each batch up to 3 times with exponential backoff when
    hitting rate limits (429).
    """
    from google import genai

    client = genai.Client(api_key=api_key)
    embeddings: list[list[float]] = []

    batch_size = 100
    max_retries = 3

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        success = False

        for attempt in range(max_retries + 1):
            try:
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                )
                embeddings.extend([e.values for e in result.embeddings])
                success = True
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait = min(35 * (2 ** attempt), 120)  # 35s, 70s, 120s
                    logger.warning(
                        "Rate limited on batch %d (attempt %d/%d), retrying in %ds…",
                        i, attempt + 1, max_retries + 1, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Embedding batch %d failed: %s", i, e)
                    break  # non-retriable error

        if not success:
            logger.error("Embedding batch %d exhausted retries — using zero vectors", i)
            embeddings.extend([[0.0] * EMBEDDING_DIM] * len(batch))

        # Delay between batches to stay under rate limits
        if i + batch_size < len(texts):
            time.sleep(2)

    return embeddings


# ---------------------------------------------------------------------------
# Chunk generators
# ---------------------------------------------------------------------------

def _generate_table_overview_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """One chunk per user table with row counts and column info."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    chunks: list[dict[str, str]] = []

    for table in tables:
        try:
            cur2 = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cur2.fetchone()[0]
            cur3 = conn.execute(f'PRAGMA table_info("{table}")')
            cols = [r[1] for r in cur3.fetchall()]

            # Date range
            date_info = ""
            if "date" in cols:
                cur4 = conn.execute(
                    f'SELECT MIN(date), MAX(date) FROM "{table}" WHERE date IS NOT NULL'
                )
                dr = cur4.fetchone()
                if dr and dr[0]:
                    date_info = f" Data spans from {str(dr[0])[:10]} to {str(dr[1])[:10]}."

            # Amount totals
            amt_info = ""
            if "amount" in cols:
                cur5 = conn.execute(
                    f'SELECT SUM(amount), AVG(amount) FROM "{table}" WHERE amount IS NOT NULL'
                )
                ar = cur5.fetchone()
                if ar and ar[0]:
                    amt_info = f" Total amount: {ar[0]:,.0f} MAD. Average per row: {ar[1]:,.0f} MAD."

            text = (
                f"Table '{table}' contains {count} rows with columns: {', '.join(cols)}.{date_info}{amt_info}"
            )
            chunks.append({"id": f"overview_{table}", "text": text, "type": "table_overview", "table": table})
        except Exception as e:
            logger.warning("Skipping table overview for %s: %s", table, e)

    return chunks


def _generate_monthly_aggregate_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Monthly aggregates from data_reel and data_reel_real."""
    chunks: list[dict[str, str]] = []

    # Check if data_reel exists
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_reel'")
    if not cur.fetchone():
        return chunks

    # Monthly nominal totals
    rows = conn.execute("""
        SELECT strftime('%Y-%m', date) AS period,
               SUM(amount) AS total,
               COUNT(*) AS txn_count,
               COUNT(DISTINCT partner) AS n_partners,
               COUNT(DISTINCT channel) AS n_channels
        FROM data_reel
        WHERE date IS NOT NULL
        GROUP BY period
        ORDER BY period
    """).fetchall()

    for r in rows:
        text = (
            f"In {r[0]}, nominal financial activity totaled {r[1]:,.0f} MAD "
            f"across {r[2]} transactions, involving {r[3]} partners and {r[4]} channels."
        )
        chunks.append({"id": f"monthly_nom_{r[0]}", "text": text, "type": "monthly_aggregate", "table": "data_reel"})

    # Monthly real totals
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_reel_real'")
    if cur.fetchone():
        # Find real column
        cur2 = conn.execute('PRAGMA table_info("data_reel_real")')
        real_col = None
        for row in cur2.fetchall():
            if str(row[1]).startswith("amount_real_"):
                real_col = row[1]
                break

        if real_col:
            rows_real = conn.execute(f"""
                SELECT strftime('%Y-%m', date) AS period,
                       SUM(amount) AS nominal,
                       SUM("{real_col}") AS real_val,
                       AVG(cpi_deflator) AS avg_cpi
                FROM data_reel_real
                WHERE date IS NOT NULL
                GROUP BY period
                ORDER BY period
            """).fetchall()

            for r in rows_real:
                nominal = float(r[1] or 0)
                real_val = float(r[2] or 0)
                cpi = float(r[3] or 1)
                erosion = nominal - real_val
                erosion_pct = (erosion / nominal * 100) if nominal else 0
                text = (
                    f"In {r[0]}, nominal activity was {nominal:,.0f} MAD and "
                    f"real (inflation-adjusted) activity was {real_val:,.0f} MAD. "
                    f"Purchasing power erosion: {erosion:,.0f} MAD ({erosion_pct:.1f}%). "
                    f"Average CPI deflator applied: {cpi:.4f}."
                )
                chunks.append({
                    "id": f"monthly_real_{r[0]}",
                    "text": text,
                    "type": "monthly_real",
                    "table": "data_reel_real",
                })

    return chunks


def _generate_partner_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Per-partner and per-channel totals."""
    chunks: list[dict[str, str]] = []

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_reel'")
    if not cur.fetchone():
        return chunks

    # Partner totals
    rows = conn.execute("""
        SELECT partner, SUM(amount) AS total, COUNT(*) AS cnt,
               MIN(date) AS min_date, MAX(date) AS max_date
        FROM data_reel
        WHERE date IS NOT NULL AND partner IS NOT NULL
        GROUP BY partner
        ORDER BY total DESC
    """).fetchall()

    for r in rows:
        text = (
            f"Partner '{r[0]}' generated {r[1]:,.0f} MAD in nominal revenue "
            f"across {r[2]} transactions from {str(r[3])[:10]} to {str(r[4])[:10]}."
        )
        chunks.append({"id": f"partner_{r[0]}", "text": text, "type": "partner_summary", "table": "data_reel"})

    # Channel totals
    rows2 = conn.execute("""
        SELECT channel, SUM(amount) AS total, COUNT(*) AS cnt
        FROM data_reel
        WHERE date IS NOT NULL AND channel IS NOT NULL
        GROUP BY channel
        ORDER BY total DESC
    """).fetchall()

    for r in rows2:
        text = (
            f"Distribution channel '{r[0]}' had {r[1]:,.0f} MAD total nominal volume across {r[2]} transactions."
        )
        chunks.append({"id": f"channel_{r[0]}", "text": text, "type": "channel_summary", "table": "data_reel"})

    return chunks


def _generate_econ_indicator_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Chunks from the econ_indicators table."""
    chunks: list[dict[str, str]] = []

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='econ_indicators'")
    if not cur.fetchone():
        return chunks

    # Group by indicator + year
    rows = conn.execute("""
        SELECT indicator_code, source,
               strftime('%Y', date) AS yr,
               AVG(value) AS avg_val,
               MIN(value) AS min_val,
               MAX(value) AS max_val,
               COUNT(*) AS cnt
        FROM econ_indicators
        WHERE date IS NOT NULL
        GROUP BY indicator_code, source, yr
        ORDER BY indicator_code, yr
    """).fetchall()

    indicator_labels = {
        "cpi": "Consumer Price Index (CPI)",
        "ppi": "Producer Price Index (PPI / GDP Deflator)",
        "cpi_yoy": "CPI Year-over-Year Inflation Rate",
        "policy_rate": "Bank Al-Maghrib Policy Rate",
    }

    for r in rows:
        code = r[0]
        label = indicator_labels.get(code, code)
        text = (
            f"In {r[2]}, the Morocco {label} (source: {r[1]}) "
            f"averaged {r[3]:.2f} (range: {r[4]:.2f} – {r[5]:.2f}), "
            f"based on {r[6]} observations."
        )
        chunks.append({
            "id": f"econ_{code}_{r[2]}",
            "text": text,
            "type": "econ_indicator",
            "table": "econ_indicators",
        })

    return chunks


def _generate_comparison_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Year-over-year comparisons and derived insights."""
    chunks: list[dict[str, str]] = []

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='data_reel'")
    if not cur.fetchone():
        return chunks

    # Annual comparison
    rows = conn.execute("""
        SELECT strftime('%Y', date) AS yr,
               SUM(amount) AS total,
               COUNT(*) AS cnt
        FROM data_reel
        WHERE date IS NOT NULL
        GROUP BY yr
        ORDER BY yr
    """).fetchall()

    prev_total = None
    for r in rows:
        yr_total = float(r[1] or 0)
        if prev_total and prev_total > 0:
            growth = ((yr_total - prev_total) / prev_total) * 100
            text = (
                f"Annual nominal revenue comparison: {r[0]} total was {yr_total:,.0f} MAD "
                f"vs prior year {prev_total:,.0f} MAD — a {'growth' if growth > 0 else 'decline'} "
                f"of {abs(growth):.1f}% ({r[2]} transactions)."
            )
            chunks.append({
                "id": f"yoy_{r[0]}",
                "text": text,
                "type": "year_comparison",
                "table": "data_reel",
            })
        prev_total = yr_total

    # Partner x Year breakdown (top partners)
    rows2 = conn.execute("""
        SELECT partner, strftime('%Y', date) AS yr, SUM(amount) AS total
        FROM data_reel
        WHERE date IS NOT NULL AND partner IS NOT NULL
        GROUP BY partner, yr
        ORDER BY partner, yr
    """).fetchall()

    partner_data: dict[str, list[tuple[str, float]]] = {}
    for r in rows2:
        partner_data.setdefault(r[0], []).append((r[1], float(r[2] or 0)))

    for partner, years in partner_data.items():
        if len(years) >= 2:
            last_two = years[-2:]
            yr1, val1 = last_two[0]
            yr2, val2 = last_two[1]
            if val1 > 0:
                growth = ((val2 - val1) / val1) * 100
                text = (
                    f"Partner '{partner}' grew from {val1:,.0f} MAD in {yr1} to {val2:,.0f} MAD "
                    f"in {yr2}, representing a {growth:+.1f}% change."
                )
                chunks.append({
                    "id": f"partner_yoy_{partner}_{yr2}",
                    "text": text,
                    "type": "partner_yoy",
                    "table": "data_reel",
                })

    return chunks


def _generate_balance_sheet_chunks(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Balance sheet and aging summary chunks."""
    chunks: list[dict[str, str]] = []

    # Clients aging
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
    if cur.fetchone():
        rows = conn.execute("SELECT * FROM clients LIMIT 50").fetchall()
        cur2 = conn.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in cur2.fetchall()]

        if rows:
            total_col = "total_g_n_ral" if "total_g_n_ral" in cols else None
            if total_col:
                for idx, r in enumerate(rows):
                    row_dict = dict(zip(cols, r))
                    name = row_dict.get("name", "Unknown")
                    try:
                        total = float(row_dict.get(total_col) or 0)
                    except (ValueError, TypeError):
                        continue  # skip summary/header rows with non-numeric totals
                    if total > 0:
                        text = f"Client '{name}' has total receivables of {total:,.0f} MAD in the aging report."
                        chunks.append({"id": f"client_{name}_{idx}", "text": text, "type": "clients_aging", "table": "clients"})

    # Suppliers aging
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
    if cur.fetchone():
        rows = conn.execute("SELECT * FROM suppliers LIMIT 50").fetchall()
        cur2 = conn.execute("PRAGMA table_info(suppliers)")
        cols = [r[1] for r in cur2.fetchall()]

        if rows:
            total_col = "total_g_n_ral" if "total_g_n_ral" in cols else None
            if total_col:
                for idx, r in enumerate(rows):
                    row_dict = dict(zip(cols, r))
                    name = row_dict.get("name", "Unknown")
                    try:
                        total = float(row_dict.get(total_col) or 0)
                    except (ValueError, TypeError):
                        continue  # skip summary/header rows with non-numeric totals
                    if total > 0:
                        text = f"Supplier '{name}' has total payables of {total:,.0f} MAD in the aging report."
                        chunks.append({"id": f"supplier_{name}_{idx}", "text": text, "type": "suppliers_aging", "table": "suppliers"})

    return chunks


# ---------------------------------------------------------------------------
# Main indexer
# ---------------------------------------------------------------------------

def build_index(db_path: Path | None = None, api_key: str | None = None) -> dict[str, Any]:
    """
    Build or rebuild the full ChromaDB vector index from the SQLite DB.

    Returns a status dict with chunk count, timing, etc.
    """
    import chromadb

    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"status": "error", "detail": "GEMINI_API_KEY not set"}

    conn_path = db_path or DB_PATH
    conn = sqlite3.connect(str(conn_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row

    start_time = time.time()

    try:
        # Generate all chunks
        all_chunks: list[dict[str, str]] = []
        all_chunks.extend(_generate_table_overview_chunks(conn))
        all_chunks.extend(_generate_monthly_aggregate_chunks(conn))
        all_chunks.extend(_generate_partner_chunks(conn))
        all_chunks.extend(_generate_econ_indicator_chunks(conn))
        all_chunks.extend(_generate_comparison_chunks(conn))
        all_chunks.extend(_generate_balance_sheet_chunks(conn))

        logger.info("Generated %d chunks for RAG indexing", len(all_chunks))

        if not all_chunks:
            return {"status": "warning", "detail": "No data to index", "chunks": 0}

        # Embed all texts
        texts = [c["text"] for c in all_chunks]
        embeddings = _embed_texts(texts, api_key)

        # Store in ChromaDB
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        # Delete existing collection and recreate
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # Add in batches
        batch_size = 200
        for i in range(0, len(all_chunks), batch_size):
            batch_end = min(i + batch_size, len(all_chunks))
            collection.add(
                ids=[c["id"] for c in all_chunks[i:batch_end]],
                embeddings=embeddings[i:batch_end],
                documents=[c["text"] for c in all_chunks[i:batch_end]],
                metadatas=[{"type": c.get("type", ""), "table": c.get("table", "")} for c in all_chunks[i:batch_end]],
            )

        elapsed = time.time() - start_time

        # Save timestamp
        ts_file = CHROMA_DIR / "last_indexed.txt"
        ts_file.write_text(datetime.now(tz=timezone.utc).isoformat())

        return {
            "status": "ok",
            "chunks_indexed": len(all_chunks),
            "elapsed_seconds": round(elapsed, 1),
            "collection": COLLECTION_NAME,
        }

    except Exception as e:
        logger.error("RAG indexing failed: %s", e)
        return {"status": "error", "detail": str(e)}
    finally:
        conn.close()


def get_index_status() -> dict[str, Any]:
    """Return current index health / stats."""
    import chromadb

    status: dict[str, Any] = {"collection": COLLECTION_NAME, "chroma_dir": str(CHROMA_DIR)}

    ts_file = CHROMA_DIR / "last_indexed.txt"
    if ts_file.exists():
        status["last_indexed"] = ts_file.read_text().strip()
    else:
        status["last_indexed"] = None

    try:
        if not CHROMA_DIR.exists():
            status["chunk_count"] = 0
            status["status"] = "not_indexed"
            return status

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
        status["chunk_count"] = collection.count()
        status["status"] = "ready"
    except Exception:
        status["chunk_count"] = 0
        status["status"] = "not_indexed"

    return status
