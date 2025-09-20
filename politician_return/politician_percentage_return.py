import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Load the datasets
try:
    transactions_df = pd.read_csv('selected_transactions_summary.csv')
    prices_df = pd.read_csv('stock_prices.csv')
except FileNotFoundError as e:
    print(f"Error loading data: {e}. Make sure the CSV files are in the correct directory.")
    exit()

# --- Data Preprocessing ---
transactions_df['Traded_Date'] = pd.to_datetime(transactions_df['Traded_Date'])
transactions_df = transactions_df[transactions_df['Transaction'] == 'Purchase'].copy()


def estimate_trade_size(trade_range):
    if isinstance(trade_range, str):
        trade_range = trade_range.replace(',', '')
        if '-' in trade_range:
            low, high = map(int, trade_range.split('-'))
            return (low + high) / 2
        elif '>' in trade_range:
            return int(trade_range.replace('>', ''))
        elif '<' in trade_range:
            return int(trade_range.replace('<', ''))
    return np.nan


transactions_df['Estimated_Trade_Size'] = transactions_df['Trade_Size_USD'].apply(estimate_trade_size)
transactions_df.dropna(subset=['Estimated_Trade_Size'], inplace=True)
transactions_df['trade_month'] = transactions_df['Traded_Date'].dt.to_period('M')

prices_df['Date'] = pd.to_datetime(prices_df['Date'])
prices_df['price_month'] = prices_df['Date'].dt.to_period('M')

# --- Extract S&P 500 (SPY) data for benchmark ---
spy_prices = prices_df[prices_df['Ticker'] == 'SPY'].copy()
if spy_prices.empty:
    print("Error: S&P 500 (SPY) data not found in stock_prices.csv. Cannot perform benchmark comparison.")
    exit()

# --- Merge and Calculate Base Data ---
merged_df = pd.merge(
    transactions_df,
    prices_df,
    left_on=['Ticker', 'trade_month'],
    right_on=['Ticker', 'price_month'],
    how='inner'
)
merged_df.rename(columns={'Close': 'purchase_price'}, inplace=True)


def generate_final_percentage_chart():
    """
    Calculates weighted average percentage returns for all politicians and compares
    them to the average S&P 500 returns, with final formatting.
    """
    return_dfs = []
    avg_spy_returns = {}
    base_df = merged_df.copy()

    for years_ahead in [1, 2, 3]:
        target_month_col = f'target_month_{years_ahead}y'
        future_price_col = f'future_price_{years_ahead}y'
        return_col = f'Return_{years_ahead}-Year'

        base_df[target_month_col] = base_df['trade_month'] + (12 * years_ahead)

        final_df = pd.merge(
            base_df,
            prices_df.rename(columns={'Close': future_price_col}),
            left_on=['Ticker', target_month_col],
            right_on=['Ticker', 'price_month'],
            how='inner'
        )

        final_df['profit'] = final_df['Estimated_Trade_Size'] * \
                             (final_df[future_price_col] - final_df['purchase_price']) / final_df['purchase_price']

        grouped = final_df.groupby('Name').agg(
            total_profit=('profit', 'sum'),
            total_investment=('Estimated_Trade_Size', 'sum')
        )
        grouped[return_col] = grouped['total_profit'] / grouped['total_investment']
        politician_performance = grouped[[return_col]].reset_index()

        return_dfs.append(politician_performance)

        spy_merged_df = pd.merge(base_df, spy_prices[['price_month', 'Close']].rename(columns={'Close': 'spy_start'}),
                                 left_on='trade_month', right_on='price_month')
        spy_merged_df = pd.merge(spy_merged_df,
                                 spy_prices[['price_month', 'Close']].rename(columns={'Close': 'spy_end'}),
                                 left_on=target_month_col, right_on='price_month')
        avg_spy_returns[years_ahead] = (
                    (spy_merged_df['spy_end'] - spy_merged_df['spy_start']) / spy_merged_df['spy_start']).mean()

    from functools import reduce
    combined_returns = reduce(lambda left, right: pd.merge(left, right, on='Name', how='outer'), return_dfs).fillna(0)
    combined_returns.set_index('Name', inplace=True)

    all_politicians_sorted = combined_returns.sort_values(by='Return_3-Year', ascending=False)

    # --- Plotting ---
    num_politicians = len(all_politicians_sorted)
    fig_width = max(25, num_politicians * 0.6)
    fig, ax = plt.subplots(figsize=(fig_width, 15))

    all_politicians_sorted.plot(kind='bar', ax=ax, width=0.8, color=['#1f77b4', '#ff7f0e', '#2ca02c'])

    line_colors = {'1': '#1f77b4', '2': '#ff7f0e', '3': '#2ca02c'}
    for year, avg_return in avg_spy_returns.items():
        ax.axhline(y=avg_return, color=line_colors[str(year)], linestyle='--', linewidth=2.5,
                   label=f'S&P 500 Avg Return ({year}-Year)')

    ax.set_title('Target Politicians Portfolio Return vs. S&P 500 Benchmark', fontsize=28, fontweight='bold')
    ax.set_ylabel('Weighted Average Return (%)', fontsize=20, fontweight='bold')
    ax.set_xlabel('Politician', fontsize=20, fontweight='bold')

    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))

    # --- Make x-axis labels (names) bigger and bold ---
    plt.xticks(rotation=90)
    ax.tick_params(axis='x', labelsize=16)  # Increased size
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')

    ax.tick_params(axis='y', labelsize=14)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=16)

    ax.grid(True, which='major', axis='y', linestyle='--')
    ax.axhline(0, color='black', linewidth=1.2)

    # Adjust bottom margin to make space for labels
    plt.subplots_adjust(bottom=0.3)
    plt.tight_layout()
    plt.savefig('politician_percentage_return.png')
    print("Saved plot: politician_percentage_return.png")
    plt.show()


# --- Generate the plot ---
generate_final_percentage_chart()