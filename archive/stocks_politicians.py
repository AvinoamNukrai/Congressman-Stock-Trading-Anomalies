import os
import pandas as pd
import matplotlib.pyplot as plt

OUTPUTS_DIR = "../outputs"

# רשימת הפוליטיקאים שביקשת
TARGET_POLITICIANS = [
    "Suzan K. Delbene",
    "Nancy Pelosi",
    "Roberts, Pat",
    "Wyden, Ron",
    "Daniel Meuser",
    "Capito, Shelley Moore",
    "Toomey, Pat",
    "John Curtis",
    "Bob Gibbs",
    "Susan W. Brooks",
    "Earl Blumenauer",
    "Mark Green",
    "John A. Yarmuth",
    "Mark Dr Green",
    "Brian Mast"
]

def load_prices(prices_csv):
    """Load stock prices, force header names if missing."""
    prices = pd.read_csv(prices_csv, header=None, names=["Date", "Close", "Ticker"])
    prices["Date"] = pd.to_datetime(prices["Date"], errors="coerce")
    prices["Month"] = prices["Date"].dt.to_period("M")
    prices = prices.dropna(subset=["Ticker", "Close", "Month"])
    prices = (
        prices.sort_values(["Ticker", "Date"])
              .groupby(["Ticker", "Month"], as_index=False)
              .tail(1)
    )
    return prices[["Ticker", "Month", "Close"]].rename(columns={"Close": "Price"})


def load_trades(trades_csv):
    """Load selected trades (politicians, ticker, date)."""
    trades = pd.read_csv(trades_csv)
    trades["Traded_Date"] = pd.to_datetime(trades["Traded_Date"], errors="coerce")
    trades["TradeMonth"] = trades["Traded_Date"].dt.to_period("M")
    return trades


def add_forward_returns(trades, prices, horizon=12):
    """Add expected return after horizon months for each trade."""
    merged = trades.merge(
        prices.rename(columns={"Price": "trade_price"}),
        left_on=["Ticker", "TradeMonth"],
        right_on=["Ticker", "Month"],
        how="left"
    ).drop(columns=["Month"])

    # future price
    future = prices.copy()
    future["FutureMonth"] = (future["Month"] + horizon).astype("period[M]")

    merged = merged.merge(
        future.rename(columns={"Price": f"future_price_{horizon}m"})[["Ticker", "FutureMonth", f"future_price_{horizon}m"]],
        left_on=["Ticker", "TradeMonth"],
        right_on=["Ticker", "FutureMonth"],
        how="left"
    ).drop(columns=["FutureMonth"])

    # return
    merged[f"ret_{horizon}m"] = (merged[f"future_price_{horizon}m"] - merged["trade_price"]) / merged["trade_price"]

    return merged


def plot_politicians_returns(summary, output_path, horizon="ret_12m"):
    """Plot bar chart of returns after given horizon for selected politicians."""
    df_filtered = summary[summary["Name"].isin(TARGET_POLITICIANS)].copy()

    for p in TARGET_POLITICIANS:
        if p not in df_filtered["Name"].values:
            df_filtered = pd.concat([
                df_filtered,
                pd.DataFrame({"Name": [p], horizon: [0.0]})
            ], ignore_index=True)

    df_sorted = df_filtered.sort_values(horizon, ascending=False)
    colors = ["green" if val > 0 else "red" for val in df_sorted[horizon]]

    plt.figure(figsize=(14, 8))
    bars = plt.barh(df_sorted["Name"], df_sorted[horizon], color=colors)
    plt.gca().invert_yaxis()

    plt.xlabel(f"Average Return after {horizon.replace('ret_', '').replace('m','')} Months (%)")
    plt.ylabel("Politician")
    plt.title(f"Expected {horizon.replace('ret_', '').replace('m','')}-Month Returns - Selected Politicians", fontsize=16, weight="bold")

    for bar, val in zip(bars, df_sorted[horizon]):
        plt.text(bar.get_width(), bar.get_y() + bar.get_height()/2, f"{val:.2%}",
                 va="center", ha="left", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"📊 saved plot to {output_path}")


def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    prices_csv = os.path.join(OUTPUTS_DIR, "stock_prices.csv")
    trades_csv = os.path.join(OUTPUTS_DIR, "selected_trades_suspicious.csv")

    prices = load_prices(prices_csv)
    trades = load_trades(trades_csv)

    if prices.empty or trades.empty:
        print("❌ Prices or trades are empty")
        return

    detailed = add_forward_returns(trades, prices, horizon=12)

    # summary: avg return per politician
    summary = detailed.groupby("Name", as_index=False).agg({"ret_12m": "mean"})

    out_file = os.path.join(OUTPUTS_DIR, "selected_politicians_ret_12m.png")
    plot_politicians_returns(summary, out_file, horizon="ret_12m")


if __name__ == "__main__":
    main()