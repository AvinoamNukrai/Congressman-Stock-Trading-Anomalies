"""General utility functions for dataset preparation and CSV merging."""

from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import pandas as pd


def setup_logging(level: int):
    """Configure root logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("google.api_core").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def read_with_fallback(base_path: Path, filename: str) -> pd.DataFrame:
    """Read CSV trying multiple encodings."""
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    full_path = base_path / filename
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(full_path, encoding=enc)
        except UnicodeDecodeError as e:
            last_err = e
    raise UnicodeDecodeError(
        f"All candidate encodings failed for {full_path}: {last_err}"
    )


def add_traded_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized Traded_Date column."""
    df = df.copy()
    df["Traded_Date"] = pd.to_datetime(df["Traded"], errors="coerce")
    return df


def filter_period(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Filter rows by traded date range."""
    mask = (df["Traded_Date"] >= start) & (df["Traded_Date"] <= end)
    return df.loc[mask].copy()


def filter_purchases(df: pd.DataFrame) -> pd.DataFrame:
    """Return only purchase transactions."""
    return df[df["Transaction"].str.contains("purchase", case=False, na=False)].copy()


def limit_transactions(df: pd.DataFrame, per_name: int) -> pd.DataFrame:
    """Limit number of transactions per politician."""
    return df.groupby("Name", group_keys=False).head(per_name).reset_index(drop=True)


def load_or_init_df(
    base_df: pd.DataFrame,
    output_csv: str,
    prompt_col: str,
    response_col: str,
) -> pd.DataFrame:
    """Merge existing analysis CSV if present, else initialize columns."""
    merge_cols = ["Name", "Ticker", "Traded_Date"]
    path = Path(output_csv)
    if path.exists():
        existing = pd.read_csv(output_csv)
        # Drop any columns ending with '_y' to avoid merge errors
        drop_cols = [c for c in existing.columns if c.endswith("_y")]
        if drop_cols:
            existing = existing.drop(columns=drop_cols, errors="ignore")
        if "Traded_Date" in existing and existing["Traded_Date"].dtype == object:
            with pd.option_context("mode.chained_assignment", None):
                try:
                    existing["Traded_Date"] = pd.to_datetime(existing["Traded_Date"])
                except Exception:
                    pass
        merged = base_df.merge(existing, on=merge_cols, how="left", suffixes=("", "_y"))
        resp_y = response_col + "_y"
        if resp_y in merged.columns:
            merged[response_col] = merged[response_col].fillna(merged[resp_y])
            drop_cols = [c for c in merged.columns if c.endswith("_y")]
            merged.drop(columns=drop_cols, inplace=True, errors="ignore")
        if prompt_col not in merged:
            merged[prompt_col] = pd.NA
        if response_col not in merged:
            merged[response_col] = pd.NA
        return merged
    out = base_df.copy()
    if prompt_col not in out:
        out[prompt_col] = pd.NA
    if response_col not in out:
        out[response_col] = pd.NA
    return out
