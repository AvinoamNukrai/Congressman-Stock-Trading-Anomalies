import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from functools import reduce

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

# --- Merge and Calculate Base Data ---
merged_df = pd.merge(
    transactions_df,
    prices_df,
    left_on=['Ticker', 'trade_month'],
    right_on=['Ticker', 'price_month'],
    how='inner'
)
merged_df.rename(columns={'Close': 'purchase_price'}, inplace=True)


def generate_top40_vertical_chart_final():
    """
    Calculates 1, 2, and 3-year profits and displays the Top 40 movers
    as a consolidated grouped vertical bar chart with final formatting.
    """
    profit_dfs = []
    for years_ahead in [1, 2, 3]:
        target_month_col = f'target_month_{years_ahead}y'
        future_price_col = f'future_price_{years_ahead}y'
        profit_col = f'Profit {years_ahead}-Year'  # Renamed for legend clarity

        # Create a copy to avoid modifying the base merged_df in the loop
        loop_df = merged_df.copy()
        loop_df[target_month_col] = loop_df['trade_month'] + (12 * years_ahead)

        final_df = pd.merge(
            loop_df,
            prices_df,
            left_on=['Ticker', target_month_col],
            right_on=['Ticker', 'price_month'],
            how='inner'
        )
        final_df.rename(columns={'Close': future_price_col}, inplace=True)

        final_df[profit_col] = final_df['Estimated_Trade_Size'] * \
                               (final_df[future_price_col] - final_df['purchase_price']) / final_df['purchase_price']

        politician_profits = final_df.groupby('Name')[profit_col].sum().reset_index()
        profit_dfs.append(politician_profits)

    # --- Combine yearly profits into a single DataFrame ---
    combined_profits = reduce(lambda left, right: pd.merge(left, right, on='Name', how='outer'), profit_dfs).fillna(0)
    combined_profits.set_index('Name', inplace=True)

    # Select Top 40 movers based on absolute 3-year performance
    combined_profits['abs_profit_3y'] = combined_profits['Profit 3-Year'].abs()
    top_40 = combined_profits.sort_values(by='abs_profit_3y', ascending=False).head(40)

    # Sort the Top 40 by actual profit for a logical plot order
    top_40 = top_40.sort_values(by='Profit 3-Year', ascending=False)
    top_40 = top_40.drop(columns=['abs_profit_3y'])

    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(25, 15))  # Increased height for more label space

    # Create the grouped vertical bar chart
    top_40.plot(kind='bar', ax=ax, width=0.8,
                color=['#1f77b4', '#ff7f0e', '#2ca02c'])  # Custom colors

    # Set Symmetric Log Scale on Y-axis
    ax.set_yscale('symlog')

    # --- FONT ADJUSTMENTS ---
    ax.set_title('Target Politicians Performance (1, 2, and 3 Years)', fontsize=22, fontweight='bold')
    ax.set_ylabel('Estimated Profit / Loss (USD)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Politician', fontsize=16, fontweight='bold')

    plt.xticks(rotation=90)

    # --- UPDATED SECTION TO MAKE POLITICIAN NAMES BIGGER AND BOLDER ---
    ax.tick_params(axis='x', labelsize=14)  # Increased label size
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    # --- END OF UPDATED SECTION ---

    ax.tick_params(axis='y', labelsize=12)
    ax.legend(fontsize=14)

    # Format y-axis labels as dollars
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, p: f'${y:,.0f}'))
    ax.grid(True, which='major', axis='y', linestyle='--')
    ax.axhline(0, color='black', linewidth=0.8)  # Add a line at zero

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('target_politicians_profit_loss_chart.png')
    print("Saved plot: target_politicians_profit_loss_chart.png")
    plt.show()


# --- Generate the plot ---
generate_top40_vertical_chart_final()