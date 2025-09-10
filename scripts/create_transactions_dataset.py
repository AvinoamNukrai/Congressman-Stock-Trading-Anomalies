"""
Build a limited congressional trading dataset and optionally enrich each
transaction with an AI-generated forensic conflict-of-interest analysis.
"""

import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import kagglehub
from tqdm import tqdm

from utils.load_config import load_transactions_config, get_api_key
from utils.utils import (
    setup_logging,
    read_with_fallback,
    add_traded_datetime,
    filter_period,
    filter_purchases,
    limit_transactions,
    load_or_init_df,
)
from prompts.transaction_analysis import generate_prompt, TransactionAnalysis
from utils.gemini import call_gemini


def download_dataset(dataset_id: str) -> Path:
    """Download (or reuse cached) Kaggle dataset and return its local path."""
    path = kagglehub.dataset_download(dataset_id)
    return Path(path)


def load_congress_data(base_path: Path, congress_csv: str) -> pd.DataFrame:
    """Load congressional trading CSV."""
    df = read_with_fallback(base_path, congress_csv)
    logging.info("Congressional Trading Data Shape: %s", df.shape)
    return df


def load_stock_prices(base_path: Path, prices_csv: str) -> pd.DataFrame:
    """Load stock prices CSV."""
    df = pd.read_csv(base_path / prices_csv)
    logging.info("Stock Prices Data Shape: %s", df.shape)
    return df


def process_rows(
    df_analysis: pd.DataFrame,
    *,
    prompt_col: str,
    response_col: str,
    output_csv: str,
    model_name: str,
    max_rows: Optional[int],
    dry_run: bool,
    overwrite_existing: bool,
    intermediate_every: int,
    max_workers: int,
) -> pd.DataFrame:
    """Iterate transactions, build prompts, call API (or dry run), save intermittently."""
    rows = df_analysis.copy()
    if max_rows is not None:
        rows = rows.head(max_rows)

    # Deduplicate by transaction key to avoid repeated appends across runs
    unique_key = ["Name", "Ticker", "Traded_Date"]
    rows = rows.drop_duplicates(subset=unique_key, keep="first")

    processed = 0
    api_calls = 0
    start = time.time()
    # Ensure output columns exist for each JSON field
    output_fields = [
        "subcommittees",
        "supporting_agenda",
        "supporting_agenda_explanation",
        "direct_legislative_connection",
        "direct_legislative_connection_proof",
        "subcommittee_decision",
        "subcommittee_decision_proof"
    ]
    for field in output_fields:
        if field not in rows.columns:
            rows[field] = pd.NA

    tasks_to_process = []
    for idx, row in rows.iterrows():
        already = (
            pd.notna(row.get(response_col)) and str(row.get(response_col)).strip() != ""
        )
        if already and not overwrite_existing:
            continue
        tasks_to_process.append((idx, row))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for idx, row in tasks_to_process:
            politician = row.get("Name")
            company = row.get("Ticker")
            traded_date = row.get("Traded_Date")
            if isinstance(traded_date, (pd.Timestamp, datetime)):
                date_str = traded_date.date().isoformat()
            else:
                date_str = str(traded_date) if pd.notna(traded_date) else "unknown"

            prompt = generate_prompt(
                politician_name=politician, company_name=company, date_of_event=date_str
            )
            rows.at[idx, prompt_col] = prompt

            if dry_run:
                rows.at[idx, response_col] = "DRY_RUN_RESPONSE"
                processed += 1
            else:
                future = executor.submit(
                    call_gemini,
                    prompt,
                    model_name=model_name,
                    response_schema=TransactionAnalysis,
                )
                future_to_idx[future] = idx
                api_calls += 1

        for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc="Processing transactions"):
            idx = future_to_idx[future]
            try:
                response_obj = future.result()
                rows.at[idx, response_col] = response_obj
                if isinstance(response_obj, dict):
                    for field in output_fields:
                        if field in response_obj:
                            rows.at[idx, field] = response_obj[field]
            except Exception as e:
                logging.error(f"Row {idx} generated an exception: {e}")
                rows.at[idx, response_col] = {"error": str(e)}

            processed += 1
            if processed % intermediate_every == 0 and processed > 0:
                rows.to_csv(output_csv, index=False)
                elapsed = time.time() - start
                logging.info(
                    "Progress: %d processed (API calls: %d) elapsed=%.1fs",
                    processed,
                    api_calls,
                    elapsed,
                )

    # Deduplicate before saving by the same transaction key
    rows = rows.drop_duplicates(subset=unique_key, keep="first")
    # Final checkpoint if not already saved
    if not Path(output_csv).exists() or processed > 0:
        rows.to_csv(output_csv, index=False)
    logging.info(
        "Done. Rows processed: %d | API calls: %d | Output exists: %s",
        processed,
        api_calls,
        Path(output_csv).exists(),
    )
    return rows


def main():
    """Load configuration, run data preparation and optional analysis."""
    cfg = load_transactions_config()
    setup_logging(cfg.LOG_LEVEL)

    # Ensure outputs directory exists
    try:
        Path(cfg.OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.warning("Could not create output directory for %s: %s", cfg.OUTPUT_CSV, e)

    base_path = download_dataset(cfg.DATASET_ID)
    congress_df = load_congress_data(base_path, cfg.CONGRESS_CSV_NAME)
    _stock_prices_df = load_stock_prices(base_path, cfg.STOCK_PRICES_CSV_NAME)

    congress_df = add_traded_datetime(congress_df)
    logging.info("Original dataset shape: %s", congress_df.shape)

    period_df = filter_period(congress_df, cfg.FILTER_START, cfg.FILTER_END)
    purchases_df = filter_purchases(period_df)
    logging.info("Filtered period shape: %s", period_df.shape)
    logging.info(
        "Purchases subset shape: %s | Date range: %s -> %s",
        purchases_df.shape,
        purchases_df["Traded_Date"].min(),
        purchases_df["Traded_Date"].max(),
    )

    limited_df = limit_transactions(purchases_df, cfg.MAX_TRANSACTIONS_PER_POLITICIAN)
    logging.info(
        "Limited dataset: %d transactions | Politicians: %d",
        len(limited_df),
        limited_df["Name"].nunique(),
    )

    df_analysis = load_or_init_df(
        limited_df,
        output_csv=cfg.OUTPUT_CSV,
        prompt_col=cfg.PROMPT_COL,
        response_col=cfg.RESPONSE_COL,
    )

    process_rows(
        df_analysis,
        prompt_col=cfg.PROMPT_COL,
        response_col=cfg.RESPONSE_COL,
        output_csv=cfg.OUTPUT_CSV,
        model_name=cfg.MODEL_NAME,
        max_rows=cfg.MAX_ROWS_TO_PROCESS,
        dry_run=cfg.DRY_RUN,
        overwrite_existing=cfg.OVERWRITE_EXISTING_RESPONSES,
        intermediate_every=cfg.INTERMEDIATE_SAVE_EVERY,
        max_workers=cfg.MAX_WORKERS,
    )


if __name__ == "__main__":
    main()
