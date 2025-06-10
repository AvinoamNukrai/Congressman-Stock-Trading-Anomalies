import kagglehub
import pandas as pd
from pathlib import Path

def collect_tickers(root_dir, possible_cols=("ticker", "symbol", "stock_symbol", "stock")):
    tickers = set()
    for csv in Path(root_dir).rglob("*.csv"):
        try:
            cols = pd.read_csv(csv, nrows=0).columns
            col = next((c for c in cols if c.lower() in possible_cols), None)
            if col:
                vals = pd.read_csv(csv, usecols=[col])[col]
                tickers.update(vals.dropna().str.upper().unique())
        except Exception:
            continue
    return tickers

def unique_tickers(a: set[str], b: set[str]):
    return a - b, b - a

def main():
    path_congress = kagglehub.dataset_download("shabbarank/congressional-trading-inception-to-march-23")
    path_market   = kagglehub.dataset_download("jacksoncrow/stock-market-dataset")

    t_congress = collect_tickers(path_congress)
    t_market   = collect_tickers(path_market)
    common     = t_congress & t_market

    print(f"Congress tickers : {len(t_congress):,}")
    print(f"Market tickers   : {len(t_market):,}")
    print(f"Intersection     : {len(common):,}")
    print(f"Overlap vs Congress: {len(common)/len(t_congress):.2%}")
    print(f"Overlap vs Market  : {len(common)/len(t_market):.2%}")
    print("Sample common:", sorted(common)[:20])

    only_congress, only_market = unique_tickers(t_congress, t_market)
    print(f"Only Congress : {len(only_congress):,}")
    print(f"Only Market   : {len(only_market):,}")
    print("Sample missing (Congress):", sorted(only_congress)[:20])
    print("Sample missing (Market)  :", sorted(only_market)[:20])

if __name__ == "__main__":
    main()