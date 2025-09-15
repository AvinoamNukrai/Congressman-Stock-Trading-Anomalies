import os
import pandas as pd
import matplotlib.pyplot as plt

OUTPUTS_DIR = "../outputs"

def load_prices(prices_csv):
    prices = pd.read_csv(prices_csv)
    prices["Date"] = pd.to_datetime(prices["Date"], errors="coerce")
    prices["Month"] = prices["Date"].dt.to_period("M")
    prices = prices.dropna(subset=["Ticker", "Close", "Month"])
    prices = (
        prices.sort_values(["Ticker", "Date"])
              .groupby(["Ticker", "Month"], as_index=False)
              .tail(1)
    )
    return prices[["Ticker", "Month", "Close"]].rename(columns={"Close": "Price"})


def load_transactions(trans_csv, suspicious_only=True):
    tx = pd.read_csv(trans_csv, low_memory=False)

    # Drop duplicated _y columns
    for col in list(tx.columns):
        if col.endswith("_y") and col[:-2] in tx.columns:
            tx.drop(columns=[col], inplace=True, errors="ignore")

    # Parse trade date
    if "Traded_Date" in tx.columns:
        tx["Traded_Date"] = pd.to_datetime(tx["Traded_Date"], errors="coerce")
    else:
        tx["Traded_Date"] = pd.to_datetime(tx.get("Traded", pd.NaT), errors="coerce")

    tx["TradeMonth"] = tx["Traded_Date"].dt.to_period("M")

    # Optionally filter only suspicious trades
    if suspicious_only and "direct_legislative_connection" in tx.columns:
        tx = tx[tx["direct_legislative_connection"] == True].copy()

    keep_cols = ["Name", "Ticker", "Traded_Date", "TradeMonth", "Transaction", "direct_legislative_connection"]
    keep_cols = [c for c in keep_cols if c in tx.columns]
    tx = tx[keep_cols].dropna(subset=["Ticker", "TradeMonth"])
    return tx


def add_forward_returns(tx, prices, horizons=(1, 3, 6, 9, 11)):
    merged = tx.merge(
        prices.rename(columns={"Price": "trade_price"}),
        left_on=["Ticker", "TradeMonth"],
        right_on=["Ticker", "Month"],
        how="left"
    ).drop(columns=["Month"])

    for h in horizons:
        future_key = f"future_price_{h}m"
        ret_key = f"ret_{h}m"

        future = prices.copy()
        future["FutureMonth"] = (future["Month"] + h).astype("period[M]")

        merged = merged.merge(
            future.rename(columns={"Price": future_key})[["Ticker", "FutureMonth", future_key]],
            left_on=["Ticker", "TradeMonth"],
            right_on=["Ticker", "FutureMonth"],
            how="left"
        ).drop(columns=["FutureMonth"])

        raw_return = (merged[future_key] - merged["trade_price"]) / merged["trade_price"]

        # Flip sign for sells
        if "Transaction" in merged.columns:
            merged[ret_key] = raw_return.where(
                merged["Transaction"].str.contains("purchase", case=False, na=False),
                -raw_return
            )
        else:
            merged[ret_key] = raw_return

    return merged


def export_outputs(detailed_df, out_prefix="trade_returns"):
    detailed_path = os.path.join(OUTPUTS_DIR, f"{out_prefix}_detailed.csv")
    detailed_df.to_csv(detailed_path, index=False)

    agg_dict = {c: "mean" for c in detailed_df.columns if c.startswith("ret_")}
    if "Name" in detailed_df.columns:
        summary = detailed_df.groupby("Name", as_index=False).agg(agg_dict)
    else:
        summary = pd.DataFrame()

    summary_path = os.path.join(OUTPUTS_DIR, f"{out_prefix}_by_politician.csv")
    if not summary.empty:
        summary.to_csv(summary_path, index=False)

    print(f"✅ saved detailed returns to {detailed_path}")
    if not summary.empty:
        print(f"✅ saved politician summary to {summary_path}")
    return summary


def plot_top_politicians(summary, output_path, horizon="ret_3m", top_n=10, title_prefix=""):
    if summary.empty or horizon not in summary.columns:
        print(f"⚠️ No summary data to plot for {horizon}.")
        return

    df_sorted = summary.sort_values(horizon, ascending=False).head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(df_sorted["Name"], df_sorted[horizon], color="purple")
    plt.gca().invert_yaxis()

    plt.xlabel("Average Return (%)")
    plt.ylabel("Politician")
    plt.title(f"{title_prefix} Top {top_n} Politicians by Avg {horizon}", fontsize=14)

    for i, (val) in enumerate(df_sorted[horizon]):
        plt.text(val, i, f"{val:.2%}", va="center", ha="left", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"📊 saved plot to {output_path}")


def run_pipeline(prices, trans_csv, suspicious_only, label):
    tx = load_transactions(trans_csv, suspicious_only=suspicious_only)
    if prices.empty or tx.empty:
        print(f"{label}: prices or transactions are empty")
        return

    detailed = add_forward_returns(tx, prices, horizons=(1, 3, 6, 9, 11))
    order_cols = [c for c in ["Name", "Ticker", "Traded_Date", "TradeMonth", "Transaction",
                              "trade_price",
                              "future_price_1m", "ret_1m",
                              "future_price_3m", "ret_3m",
                              "future_price_6m", "ret_6m",
                              "future_price_9m", "ret_9m",
                              "future_price_11m", "ret_11m",
                              "direct_legislative_connection"] if c in detailed.columns]
    detailed = detailed[order_cols].sort_values(["Name", "Traded_Date", "Ticker"])

    summary = export_outputs(detailed, out_prefix=f"trade_returns_{label}")

    # Plot for each horizon
    for h in ["ret_1m", "ret_3m", "ret_6m", "ret_9m", "ret_11m"]:
        out_file = os.path.join(OUTPUTS_DIR, f"top_politicians_{label}_{h}.png")
        plot_top_politicians(summary, out_file, horizon=h, top_n=10, title_prefix=label)


def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    prices_csv = os.path.join(OUTPUTS_DIR, "stock_prices.csv")
    trans_csv = os.path.join(OUTPUTS_DIR, "transactions_with_analysis.csv")

    prices = load_prices(prices_csv)

    # suspicious only
    run_pipeline(prices, trans_csv, suspicious_only=True, label="suspicious")

    # all trades
    run_pipeline(prices, trans_csv, suspicious_only=False, label="all")


if __name__ == "__main__":
    main()