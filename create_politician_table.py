"""Build politician profile and collaboration tables from transactions_with_analysis.csv.

Tables:
1. Politician Profiles (one row per unique Name):
   Columns: politician_name, sex, party, age, seniority_in_congress, state, city,
            university, sponership_compaines_tickets, 116_congress_committees
   (age computed as of REFERENCE_DATE)

2. Politician Collaboration (pairwise):
   Columns: politican_1, politican_2, legislative_collaboration,
            num_common_sponership_compaines_tickets, common_116_congress_committees
"""
from __future__ import annotations
import itertools
import json
import logging
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Sequence

import pandas as pd
from tqdm import tqdm

from utils.load_config import load_politician_network_config
from utils.utils import setup_logging
from utils.gemini import call_gemini
from prompts.politician_profiles import generate_profile_prompt, PoliticianProfile
from prompts.politician_collaboration import generate_collaboration_prompt, PoliticianCollaboration

REFERENCE_DATE = date(2021, 1, 3)  # End of 116th Congress

DEFAULT_PROFILES_CSV = Path("outputs/politician_profiles.csv")
DEFAULT_COLLAB_CSV = Path("outputs/politician_collaborations.csv")

COL_NAME = "Name"
COL_POLITICIAN_NAME = "politician_name"
COL_POLITICIAN_1 = "politican_1"
COL_POLITICIAN_2 = "politican_2"
PROFILE_COLUMNS = [
    "politician_name",
    "sex",
    "party",
    "age",
    "seniority_in_congress",
    "state",
    "city",
    "university",
    "sponership_compaines_tickets",
    "116_congress_committees",
]
COLLAB_COLUMNS = [
    "politican_1",
    "politican_2",
    "legislative_collaboration",
    "num_common_sponership_compaines_tickets",
    "common_116_congress_committees",
    "legislative_collaboration_evidence",
]


def compute_age(
        birth_date_str: Optional[str],
        ref_date: date = REFERENCE_DATE
) -> Optional[int]:
    """Compute age from birth date string as of reference date.

    Args:
        birth_date_str: Birth date in 'YYYY-MM-DD' format.
        ref_date: Reference date for age calculation.

    Returns:
        Age in years, or None if invalid input.
    """
    if not birth_date_str or birth_date_str in {"null", "None", ""}:
        return None
    try:
        dt = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        years = ref_date.year - dt.year - ((ref_date.month, ref_date.day) < (dt.month, dt.day))
        return max(years, 0)
    except Exception:
        return None


def load_transactions(
        csv_path: Path
) -> pd.DataFrame:
    """Load transactions CSV and validate required columns.

    Args:
        csv_path: Path to transactions CSV.

    Returns:
        DataFrame with transaction data.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If required column missing.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Transactions file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if COL_NAME not in df.columns:
        raise ValueError(f"Expected '{COL_NAME}' column in transactions CSV")
    return df


def prepare_profile_targets(
        df: pd.DataFrame
) -> List[str]:
    """Extract and sort unique politician names from DataFrame.

    Args:
        df: DataFrame containing transaction data.

    Returns:
        Sorted list of unique politician names.
    """
    names = (
        df[COL_NAME].dropna().astype(str).str.strip().replace({"": pd.NA}).dropna().unique().tolist()
    )
    names.sort()
    return names


def existing_profiles(
        path: Path
) -> pd.DataFrame:
    """Load existing politician profiles from CSV.

    Args:
        path: Path to profiles CSV.

    Returns:
        DataFrame of profiles, or empty DataFrame if not found.
    """
    if path.exists():
        try:
            df = pd.read_csv(path)
            return df
        except Exception:
            logging.warning("Failed reading existing profiles at %s; ignoring", path)
    return pd.DataFrame(columns=PROFILE_COLUMNS)


def existing_collabs(
        path: Path
) -> pd.DataFrame:
    """Load existing collaborations from CSV.

    Args:
        path: Path to collaborations CSV.

    Returns:
        DataFrame of collaborations, or empty DataFrame if not found.
    """
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception:
            logging.warning("Failed reading existing collaborations at %s; ignoring", path)
    return pd.DataFrame(columns=COLLAB_COLUMNS)


def process_profiles(
        names: List[str],
        *,
        model_name: str,
        out_path: Path,
        dry_run: bool,
        overwrite: bool,
        max_workers: int,
        max_items: Optional[int] = None,
        intermediate_every: int = 10,
) -> pd.DataFrame:
    """Generate or load politician profiles and save to CSV.

    Args:
        names: List of politician names.
        model_name: Model name for profile generation.
        out_path: Output CSV path.
        dry_run: If True, generate dummy data.
        overwrite: If True, overwrite existing data.
        max_workers: Number of parallel workers.
        max_items: Max profiles to process.
        intermediate_every: Save interim results every N items.

    Returns:
        DataFrame of all profiles.
    """
    existing = existing_profiles(out_path)
    processed_names = set()
    if not overwrite and not existing.empty:
        processed_names = set(existing[COL_POLITICIAN_NAME].astype(str))

    targets = [n for n in names if n not in processed_names]
    if max_items is not None:
        targets = targets[:max_items]
    logging.info("Profile targets: %d (skipping %d existing)", len(targets), len(processed_names))

    rows: List[Dict[str, Any]] = []
    if dry_run:
        for name in targets:
            rows.append(
                {
                    "politician_name": name,
                    "sex": "unknown",
                    "party": None,
                    "age": None,
                    "seniority_in_congress": None,
                    "state": None,
                    "city": None,
                    "university": None,
                    "sponership_compaines_tickets": json.dumps([]),
                    "116_congress_committees": json.dumps([]),
                }
            )
        df_new = pd.DataFrame(rows, columns=PROFILE_COLUMNS)
        merged = pd.concat([existing, df_new], ignore_index=True).drop_duplicates(
            subset=[COL_POLITICIAN_NAME], keep="last"
        )
        merged.to_csv(out_path, index=False)
        return merged

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for name in targets:
            prompt = generate_profile_prompt(name)
            fut = pool.submit(
                call_gemini,
                prompt,
                model_name=model_name,
                response_schema=PoliticianProfile,
            )
            futures[fut] = name

        processed = 0
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Processing profiles"):
            name = futures[fut]
            data = fut.result()
            if not data:
                logging.warning("No data for %s", name)
                continue
            age = compute_age(data.get("birth_date"))
            row = {
                "politician_name": name,
                "sex": data.get("sex"),
                "party": data.get("party"),
                "age": age,
                "seniority_in_congress": data.get("seniority_in_congress_years"),
                "state": data.get("state"),
                "city": data.get("city"),
                "university": data.get("university"),
                "sponership_compaines_tickets": json.dumps(
                    data.get("companies_sponsorships", [])
                ),
                "116_congress_committees": json.dumps(data.get("committees_116", [])),
            }
            rows.append(row)
            processed += 1
            if processed % intermediate_every == 0:
                _save_interim_results(
                    out_path=out_path,
                    existing_df=existing,
                    new_rows=rows,
                    dedupe_cols=[COL_POLITICIAN_NAME],
                    total_items=len(futures),
                    processed_count=processed,
                    item_type="profiles",
                )

    df_new = pd.DataFrame(rows, columns=PROFILE_COLUMNS)
    merged = pd.concat([existing, df_new], ignore_index=True).drop_duplicates(
        subset=[COL_POLITICIAN_NAME], keep="last"
    )
    return merged


def generate_pairs(
        names: Sequence[str]
) -> List[Tuple[str, str]]:
    """Generate sorted unique pairs of politician names.

    Args:
        names: Sequence of politician names.

    Returns:
        List of unique name pairs.
    """
    return list(itertools.combinations(sorted(set(names)), 2))


def process_collaborations(
        pairs: List[Tuple[str, str]],
        *,
        model_name: str,
        out_path: Path,
        dry_run: bool,
        overwrite: bool,
        max_workers: int,
        max_items: Optional[int] = None,
        intermediate_every: int = 20,
) -> pd.DataFrame:
    """Generate or load politician collaborations and save to CSV.

    Args:
        pairs: List of politician name pairs.
        model_name: Model name for collaboration generation.
        out_path: Output CSV path.
        dry_run: If True, generate dummy data.
        overwrite: If True, overwrite existing data.
        max_workers: Number of parallel workers.
        max_items: Max collaborations to process.
        intermediate_every: Save interim results every N items.

    Returns:
        DataFrame of all collaborations.
    """
    existing = existing_collabs(out_path)
    existing_pairs = set()
    if not overwrite and not existing.empty:
        for _, r in existing.iterrows():
            existing_pairs.add(tuple(sorted((r[COL_POLITICIAN_1], r[COL_POLITICIAN_2]))))

    targets = [p for p in pairs if p not in existing_pairs]
    if max_items is not None:
        targets = targets[:max_items]
    logging.info(
        "Collaboration pairs: %d (skipping %d existing)", len(targets), len(existing_pairs)
    )

    rows: List[Dict[str, Any]] = []
    if dry_run:
        for a, b in targets:
            rows.append(
                {
                    "politican_1": a,
                    "politican_2": b,
                    "legislative_collaboration": False,
                    "num_common_sponership_compaines_tickets": 0,
                    "common_116_congress_committees": json.dumps([]),
                    "legislative_collaboration_evidence": None,
                }
            )
        df_new = pd.DataFrame(rows, columns=COLLAB_COLUMNS)
        merged = pd.concat([existing, df_new], ignore_index=True).drop_duplicates(
            subset=[COL_POLITICIAN_1, COL_POLITICIAN_2], keep="last"
        )
        merged.to_csv(out_path, index=False)
        return merged

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for a, b in targets:
            prompt = generate_collaboration_prompt(a, b)
            fut = pool.submit(
                call_gemini,
                prompt,
                model_name=model_name,
                response_schema=PoliticianCollaboration,
            )
            futures[fut] = (a, b)

        processed = 0
        for fut in tqdm(as_completed(futures), total=len(futures), desc="Processing collaborations"):
            a, b = futures[fut]
            data = fut.result()
            if not data:
                logging.warning("No data for pair (%s, %s)", a, b)
                continue
            companies = data.get("common_sponsorship_companies", [])
            committees = data.get("common_committees_116", [])
            row = {
                "politican_1": data.get("politician_1") or a,
                "politican_2": data.get("politician_2") or b,
                "legislative_collaboration": data.get("legislative_collaboration"),
                "num_common_sponership_compaines_tickets": len(companies),
                "common_116_congress_committees": json.dumps(committees),
                "legislative_collaboration_evidence": data.get(
                    "legislative_collaboration_evidence"
                ),
            }
            rows.append(row)
            processed += 1
            if processed % intermediate_every == 0:
                _save_interim_results(
                    out_path=out_path,
                    existing_df=existing,
                    new_rows=rows,
                    dedupe_cols=[COL_POLITICIAN_1, COL_POLITICIAN_2],
                    total_items=len(futures),
                    processed_count=processed,
                    item_type="collaborations",
                )

    df_new = pd.DataFrame(rows, columns=COLLAB_COLUMNS)
    merged = pd.concat([existing, df_new], ignore_index=True).drop_duplicates(
        subset=[COL_POLITICIAN_1, COL_POLITICIAN_2], keep="last"
    )
    return merged


def main():
    """Main function to build politician profiles and collaborations."""
    cfg = load_politician_network_config()
    log_level_str = cfg.LOG_LEVEL
    setup_logging(getattr(logging, log_level_str.upper(), logging.INFO))

    transactions_csv = Path(cfg.TRANSACTIONS_CSV)
    profiles_out = Path(getattr(cfg, 'PROFILES_OUT', DEFAULT_PROFILES_CSV))
    collab_out = Path(getattr(cfg, 'COLLABORATIONS_OUT', DEFAULT_COLLAB_CSV))
    model_name = cfg.MODEL_NAME

    dry_run = cfg.DRY_RUN
    overwrite = cfg.OVERWRITE
    max_profiles = getattr(cfg, 'MAX_PROFILES', None)
    max_pairs = getattr(cfg, 'MAX_PAIRS', None)
    max_workers = cfg.MAX_WORKERS
    intermediate_every = cfg.INTERMEDIATE_EVERY

    profiles_out.parent.mkdir(parents=True, exist_ok=True)
    collab_out.parent.mkdir(parents=True, exist_ok=True)

    logging.info("Input transactions: %s", transactions_csv)
    df_tx = load_transactions(transactions_csv)

    unique_names = prepare_profile_targets(df_tx)
    logging.info("Unique politicians: %d", len(unique_names))

    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        max_profiles = int(sys.argv[1])
        logging.info("Overriding max_profiles from command line: %d", max_profiles)

    t0 = time.time()
    profiles_df = process_profiles(
        unique_names,
        model_name=model_name,
        out_path=profiles_out,
        dry_run=dry_run,
        overwrite=overwrite,
        max_workers=max_workers,
        max_items=max_profiles,
        intermediate_every=intermediate_every,
    )
    profiles_df.to_csv(profiles_out, index=False)
    logging.info("Profiles complete: %d rows", len(profiles_df))

    if (max_pairs is not None and max_pairs == 0):
        logging.info("Skipping pairwise collaboration (max_pairs=0)")
        return

    pairs = generate_pairs(profiles_df[COL_POLITICIAN_NAME].tolist())
    logging.info("Total pairs: %d", len(pairs))

    collaborations_df = process_collaborations(
        pairs,
        model_name=model_name,
        out_path=collab_out,
        dry_run=dry_run,
        overwrite=overwrite,
        max_workers=max_workers,
        max_items=max_pairs,
        intermediate_every=max(5, intermediate_every),
    )
    collaborations_df.to_csv(collab_out, index=False)
    logging.info("Collaborations complete: %d rows", len(collaborations_df))
    logging.info("All done in %.1fs", time.time() - t0)


def _save_interim_results(
        out_path: Path,
        existing_df: pd.DataFrame,
        new_rows: List[Dict[str, Any]],
        dedupe_cols: List[str],
        total_items: int,
        processed_count: int,
        item_type: str,
):
    """Save intermediate results to a CSV file.

    Args:
        out_path: Output CSV path.
        existing_df: Existing DataFrame.
        new_rows: List of new rows to add.
        dedupe_cols: Columns to deduplicate on.
        total_items: Total items to process.
        processed_count: Number processed so far.
        item_type: Type of item being processed.
    """
    interim_df = pd.DataFrame(new_rows)
    merged = pd.concat([existing_df, interim_df], ignore_index=True).drop_duplicates(
        subset=dedupe_cols, keep="last"
    )
    merged.to_csv(out_path, index=False)
    logging.info("Saved intermediate %s at %d/%d", item_type, processed_count, total_items)


if __name__ == "__main__":
    main()
