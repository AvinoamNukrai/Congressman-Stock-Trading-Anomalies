import os
import pandas as pd
import matplotlib.pyplot as plt

OUTPUTS_DIR = "../outputs"

def top_gaining_companies_line(prices_csv, output_csv, output_png, top_n=10):
    # Load stock prices
    prices = pd.read_csv(prices_csv)
    prices["Date"] = pd.to_datetime(prices["Date"], errors="coerce")

    # Compute first and last price for each ticker
    grouped = prices.sort_values(["Ticker", "Date"]).groupby("Ticker")
    summary = grouped["Close"].agg(["first", "last"]).reset_index()
    summary["ReturnPct"] = (summary["last"] - summary["first"]) / summary["first"]
    summary = summary.dropna(subset=["ReturnPct"])

    # Pick top N tickers
    top = summary.sort_values("ReturnPct", ascending=False).head(top_n)
    top_tickers = top["Ticker"].tolist()

    # Save to CSV
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUTS_DIR, output_csv)
    top.to_csv(csv_path, index=False)

    # Filter prices for top tickers
    top_prices = prices[prices["Ticker"].isin(top_tickers)]

    # Plot line chart
    plt.figure(figsize=(12, 7))
    for ticker in top_tickers:
        subset = top_prices[top_prices["Ticker"] == ticker]
        plt.plot(subset["Date"], subset["Close"], label=ticker)

    plt.xlabel("Date")
    plt.ylabel("Stock Price (USD)")
    plt.title(f"Top {top_n} Gaining Companies (Line Chart)", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)

    png_path = os.path.join(OUTPUTS_DIR, output_png)
    plt.tight_layout()
    plt.savefig(png_path, dpi=300)
    plt.close()

    print(f"✅ Saved top gainers to {csv_path} and {png_path}")
    return top


def main():
    prices_csv = os.path.join(OUTPUTS_DIR, "stock_prices.csv")
    output_csv = "top_gainers.csv"
    output_png = "top_gainers_line.png"

    top = top_gaining_companies_line(prices_csv, output_csv, output_png, top_n=10)
    print(top)


if __name__ == "__main__":
    main()