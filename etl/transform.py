"""
TRANSFORM – Clean, normalise, and reshape raw DataFrames
from the DISLOG Business Review workbook.
"""

import logging

import pandas as pd

from config.settings import DROP_FULL_NA_ROWS

logger = logging.getLogger(__name__)


# ── Generic helpers ──────────────────────────────────────────────────────────

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip whitespace, replace non-word chars with underscores."""
    df.columns = (
        df.columns.astype(str)
          .str.strip()
          .str.lower()
          .str.replace(r"[^\w]+", "_", regex=True)
          .str.strip("_")
    )
    return df


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where ALL values are NaN."""
    if DROP_FULL_NA_ROWS:
        before = len(df)
        df = df.dropna(how="all")
        dropped = before - len(df)
        if dropped:
            logger.info("  Dropped %d fully-empty rows", dropped)
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed:
        logger.info("  Removed %d duplicate rows", removed)
    return df


# ── Sheet-specific transforms ───────────────────────────────────────────────

def transform_data_reel(df: pd.DataFrame) -> pd.DataFrame:
    """Transform actual revenue/sales data (DATA_REEL cols A-G)."""
    df = clean_column_names(df)
    # Standardise column names
    rename = {
        "partenaire": "partner",
        "marque": "brand",
        "channel": "channel",
        "machine": "machine",
        "mois": "month",
        "year": "year",
        "amount": "amount",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    df = drop_empty_rows(df)

    # Ensure types
    for col in ("month", "year"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Build a proper date column from month + year
    valid_mask = df["year"].notna() & df["month"].notna()
    df.loc[valid_mask, "date"] = pd.to_datetime(
        df.loc[valid_mask, "year"].astype(int).astype(str) + "-"
        + df.loc[valid_mask, "month"].astype(int).astype(str).str.zfill(2) + "-01"
    )

    # Clean string columns
    for col in ("partner", "brand", "channel", "machine"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = deduplicate(df)
    return df


def transform_budget(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Transform a budget sub-table (Topline, Topline Net Net, Margin)."""
    df = clean_column_names(df)
    df = drop_empty_rows(df)

    # Normalise whatever columns we got
    col_map = {}
    for c in df.columns:
        low = c.lower()
        if "partenaire" in low:
            col_map[c] = "partner"
        elif "channel" in low:
            col_map[c] = "channel"
        elif "mois" in low:
            col_map[c] = "month"
        elif "amount" in low:
            col_map[c] = "amount"
        elif "comptes" in low:
            col_map[c] = "account_code"
    df = df.rename(columns=col_map)

    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    for col in ("partner", "channel"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["budget_type"] = label
    df = deduplicate(df)
    return df


def transform_data_bilan(df: pd.DataFrame) -> pd.DataFrame:
    """Transform balance sheet data – melt monthly columns into long format."""
    df = clean_column_names(df)
    df = drop_empty_rows(df)

    # Identify date columns (timestamps parsed by pandas from the Excel)
    id_cols = []
    date_cols = []
    for c in df.columns:
        # Check if col name looks like a date (e.g. "2023-01-01 00:00:00")
        try:
            pd.Timestamp(c)
            date_cols.append(c)
        except (ValueError, TypeError):
            id_cols.append(c)

    if date_cols:
        df_long = df.melt(
            id_vars=id_cols,
            value_vars=date_cols,
            var_name="date",
            value_name="amount",
        )
        df_long["date"] = pd.to_datetime(df_long["date"], errors="coerce")
        df_long["amount"] = pd.to_numeric(df_long["amount"], errors="coerce").fillna(0)
        return df_long

    return df


def transform_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Transform account mapping table."""
    df = clean_column_names(df)
    df = drop_empty_rows(df)

    rename = {
        "comptes": "account_code",
        "n1": "level_1",
        "n2": "level_2",
        "n3": "level_3",
        "n4": "level_4",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    if "account_code" in df.columns:
        df["account_code"] = df["account_code"].astype(str).str.strip()

    df = deduplicate(df)
    return df


def transform_aging(df: pd.DataFrame, entity_type: str) -> pd.DataFrame:
    """Transform client or supplier aging data."""
    df = clean_column_names(df)
    df = drop_empty_rows(df)

    # First column is the entity name
    first_col = df.columns[0]
    df = df.rename(columns={first_col: "name"})
    df["entity_type"] = entity_type

    # Fill numeric NaNs with 0 (aging buckets)
    numeric_cols = df.select_dtypes(include="number").columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()

    df = deduplicate(df)
    return df


def transform_hr_synthesis(df: pd.DataFrame) -> pd.DataFrame:
    """Transform HR synthesis – melt monthly date columns into long format."""
    df = clean_column_names(df)
    df = drop_empty_rows(df)

    # Identify id columns vs date-value columns
    id_cols = []
    date_cols = []
    for c in df.columns:
        try:
            pd.Timestamp(c)
            date_cols.append(c)
        except (ValueError, TypeError):
            id_cols.append(c)

    if date_cols:
        df_long = df.melt(
            id_vars=id_cols,
            value_vars=date_cols,
            var_name="date",
            value_name="value",
        )
        df_long["date"] = pd.to_datetime(df_long["date"], errors="coerce")
        df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
        return df_long

    return df


# ── Dispatcher ───────────────────────────────────────────────────────────────

# Map source_key → transform function
_TRANSFORM_DISPATCH = {
    "data_reel": transform_data_reel,
    "data_budget_topline": lambda df: transform_budget(df, "topline_net"),
    "data_budget_topline_net": lambda df: transform_budget(df, "topline_net_net"),
    "data_budget_margin": lambda df: transform_budget(df, "margin_net_net"),
    "data_budget_pl": lambda df: transform_budget(df, "pl_accounts"),
    "data_bilan": transform_data_bilan,
    "mapping": transform_mapping,
    "mapping_opex": transform_mapping,
    "clients": lambda df: transform_aging(df, "client"),
    "suppliers": lambda df: transform_aging(df, "supplier"),
    "hr_synthesis": transform_hr_synthesis,
}


def transform(df: pd.DataFrame, source_key: str) -> pd.DataFrame:
    """Run the appropriate transform for a given source key."""
    logger.info("Transforming '%s' (%d rows) …", source_key, len(df))

    func = _TRANSFORM_DISPATCH.get(source_key)
    if func:
        df = func(df)
    else:
        # Fallback: generic cleaning
        df = clean_column_names(df)
        df = drop_empty_rows(df)
        df = deduplicate(df)

    logger.info("  → Result: %d rows × %d columns", len(df), len(df.columns))
    return df


def transform_all(
    frames: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Transform every DataFrame in the dict."""
    return {key: transform(df, key) for key, df in frames.items()}
