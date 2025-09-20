import pandas as pd
import yfinance as yf
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUTS_DIR = "../stocks prices and target politicians/archive"

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


def build_stock_prices_csv(output_csv, start="2020-01-01", end="2020-12-31", max_workers=8):
    """
    Fetch monthly stock prices for all tickers appearing in the transactions file
    using parallel requests, and save them into a CSV.
    """
    # Load transactions and extract tickers
    tickers = ['ABBV', 'AAPL', 'JNJ', 'EMR', 'ETP', 'NLY', 'ORCL', 'VZ', 'IPWR', 'TLRY', 'BEEM', 'ZUO', 'RXT', 'PSNL', 'BGFV', 'SDC', 'UNH', 'AMT', 'PSX', 'WFC', 'ABT', 'MSFT', 'JPM', 'GOOG', 'DIS', 'V', 'GOOGL', 'NWN', 'SAP', 'BX', 'F', 'ICE', 'INTC', 'FE', 'POR', 'HPQ', 'VOD', 'BLK', 'CVS', 'AMGN', 'BAC', 'CRM', 'MDT', 'ACN', 'SBUX', 'FRC', 'HD', 'GD', 'SCHW', 'UL', 'DGX', 'VIAC', 'CB', 'CGC', 'ACB', 'CRON', 'GWPH', 'ARNA', 'APHA', 'HUM', 'MNST', 'FB', 'PLD', 'LUV', 'ROST', 'GS', 'LIN', 'NFLX', 'EBAY', 'SPGI', 'CCI', 'TGT', 'C', 'APD', 'TMUS', 'COP', 'HON', 'XOM', 'TMO', 'COST', 'CSX', 'TXN', 'ADBE', 'DHR', 'MRK', 'ATVI', 'CME', 'PEP', 'MA', 'CMCSA', 'WM', 'AXP', 'CVX', 'PG', 'ANTM', 'LRCX', 'DE', 'LMT', 'NVDA', 'UNP', 'ISRG', 'ZTS', 'AMAT', 'BDX', 'LVS', 'AMZA', 'NGL', 'ET', 'AM', 'SHLX', 'USAC', 'USDP', 'CEQP', 'PBFX', 'GEL', 'GMLP', 'ENLC', 'GLOP', 'ENBL', 'AB', 'TSLA', 'CRWD', 'PYPL', 'WORK', 'AMZN', 'BA', 'SQ', 'PLUG', 'EXPI', 'ZM', 'W', 'DAL', 'WMT', 'BBY', 'GLD', 'GOLD', 'NVAX', 'GE', 'QCOM', 'KO', 'SHOP', 'AIV', 'NKLA', 'WDAY', 'IRBT', 'UPS', 'FDX', 'AMWD', 'KR', 'DHI', 'LOW', 'PSA', 'COUP', 'BYND', 'CLX', 'SPY']

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
    output_csv = "stock_prices.csv"

    df = build_stock_prices_csv(
        output_csv,
        start="2020-01-01", end="2023-12-31",
        max_workers=8
    )
    if df is not None:
        print(df.head(10))