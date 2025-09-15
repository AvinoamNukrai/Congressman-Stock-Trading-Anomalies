import pandas as pd
import yfinance as yf
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUTS_DIR = "../outputs"

def fetch_prices(ticker, start, end):
    """Download monthly prices for a single ticker."""
    try:
        print(f"Downloading {ticker}...")
        df = yf.download(ticker, start=start, end=end, interval="1mo", progress=False)
        if df.empty:
            return None

        # Flatten MultiIndex if exists
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        # Keep only Date, Ticker, Close
        df = df.reset_index()[["Date", "Close"]]
        df["Ticker"] = ticker

        # Ensure unique columns
        df = df.loc[:, ~df.columns.duplicated()]

        return df.dropna()
    except Exception as e:
        print(f"❌ Failed {ticker}: {e}")
        return None


def build_stock_prices_csv(transactions_csv, output_csv, start="2020-01-01", end="2020-12-31", max_workers=8):
    """
    Fetch monthly stock prices for all tickers appearing in the transactions file
    using parallel requests, and save them into a CSV.
    """
    # Load transactions and extract tickers
    transactions = pd.read_csv(transactions_csv)
    tickers = transactions["Ticker"].dropna().unique().tolist()
    print(f"✅ Found {len(tickers)} unique tickers in transactions.")

    all_data = []

    # Parallel fetching
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_prices, t, start, end) for t in tickers]
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                # reset index to avoid concat problems
                result = result.reset_index(drop=True)
                all_data.append(result)

    if not all_data:
        print("❌ No stock price data was downloaded.")
        return

    # Concatenate into one dataframe
    stock_prices = pd.concat(all_data, ignore_index=True)

    # Save to CSV
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUTS_DIR, output_csv)
    stock_prices.to_csv(output_path, index=False)

    print(f"✅ Saved stock prices to {output_path}")
    return stock_prices


if __name__ == "__main__":
    transactions_csv = os.path.join(OUTPUTS_DIR, "transactions_with_analysis.csv")
    output_csv = "stock_prices.csv"

    df = build_stock_prices_csv(
        transactions_csv, output_csv,
        start="2020-01-01", end="2020-12-31",
        max_workers=8
    )
    if df is not None:
        print(df.head(10))