from pathlib import Path
import sys
import kagglehub
import pandas as pd

# Accept any column whose *name contains* one of these tokens (case-insensitive)
POSSIBLE_COLS = ("ticker", "symbol", "stock_symbol", "stock", "ticker_symbol")


def collect_tickers(root_dir: Path, debug: bool = False) -> set[str]:
    tickers: set[str] = set()

    for csv_path in root_dir.rglob("*.csv"):
        try:
            cols = pd.read_csv(csv_path, nrows=0).columns
            col = next(
                (c for c in cols if any(token in c.lower() for token in POSSIBLE_COLS)),
                None,
            )
            if col is None:
                if debug:
                    print(f"[SKIP] {csv_path.name:35} | no ticker column found")
                continue

            vals = (
                pd.read_csv(csv_path, usecols=[col], dtype={col: str})[col]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
                .unique()
            )
            tickers.update(vals)

            if debug:
                print(f"[OK]   {csv_path.name:35} | {len(vals):>5} tickers")
        except Exception as e:
            if debug:
                print(f"[ERR]  {csv_path.name:35} | {e}")
            continue

    return tickers


def diff_sets(a: set[str], b: set[str]) -> tuple[set[str], set[str]]:
    return a - b, b - a


def summarize_dataset(path: Path, name: str):
    print(f"\n--- Summary for {name} dataset ---")

    total_bytes = sum(f.stat().st_size for f in path.rglob("*.csv"))
    print(f"Total size on disk: {total_bytes / (1024 ** 2):.2f} MB")

    largest_csv = max(path.rglob("*.csv"), key=lambda f: f.stat().st_size, default=None)
    if largest_csv:
        try:
            df = pd.read_csv(largest_csv, nrows=100)
            print(f"Column types (from {largest_csv.name}):")
            print(df.dtypes)
        except Exception as e:
            print(f"Error reading {largest_csv.name}: {e}")
    else:
        print("No CSV files found.")


def main(debug: bool = False) -> None:
    path_congress = Path(
        kagglehub.dataset_download("shabbarank/congressional-trading-inception-to-march-23")
    )
    path_market = Path(kagglehub.dataset_download("jacksoncrow/stock-market-dataset"))

    summarize_dataset(path_congress, "Congress")
    summarize_dataset(path_market, "Market")

    t_congress = collect_tickers(path_congress, debug=debug)
    t_market = collect_tickers(path_market, debug=debug)
    common = t_congress & t_market

    print(f"\nCongress tickers      : {len(t_congress):,}")
    print(f"Market tickers        : {len(t_market):,}")
    print(f"Intersection          : {len(common):,}")
    print(f"Overlap vs Congress   : {len(common)/len(t_congress):.2%}")
    print(f"Overlap vs Market     : {len(common)/len(t_market):.2%}")
    print("Sample common         :", sorted(common)[:20])

    only_congress, only_market = diff_sets(t_congress, t_market)
    print(f"\nOnly Congress (missing in market) : {len(only_congress):,}")
    print("Sample:", sorted(only_congress)[:20])
    print(f"\nOnly Market (missing in congress) : {len(only_market):,}")
    print("Sample:", sorted(only_market)[:20])


if __name__ == "__main__":
    main(debug="--debug" in sys.argv)