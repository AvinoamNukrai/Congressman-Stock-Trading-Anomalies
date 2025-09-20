import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Constants ---
# The name of the input CSV file.
STOCK_PRICES_FILE = 'stock_prices_2.csv'

# A list of the stock tickers you want to visualize.
TICKERS_TO_PLOT = ['UNH', 'GOOG', 'BA', 'LMT', 'AMZN', 'JPM', 'MSFT']

# The desired name for the output image file.
OUTPUT_PNG_FILE = 'normalized_stock_performance_2020.png'


# --- Function Definition ---
def plot_normalized_price_increase_2020(prices_csv, tickers_to_plot, output_png):
    """
    Creates and saves a normalized line chart showing the stock price evolution
    for a given list of tickers, filtered for the year 2020.
    """
    # 1. Read the data from the CSV file
    try:
        df = pd.read_csv(prices_csv)
    except FileNotFoundError:
        print(f"Error: The file '{prices_csv}' was not found.")
        return

    # 2. Prepare the data
    df['Date'] = pd.to_datetime(df['Date'])
    df_2020 = df[df['Date'].dt.year == 2020].copy()  # Use .copy() to avoid warnings
    df_filtered = df_2020[df_2020['Ticker'].isin(tickers_to_plot)].copy()

    # --- THIS IS THE NEW NORMALIZATION PART ---
    # For each ticker, divide its price by its first price in the period and multiply by 100
    df_filtered['Normalized Price'] = df_filtered.groupby('Ticker')['Close'].transform(lambda x: (x / x.iloc[0]) * 100)

    # Check if there's any data to plot
    if df_filtered.empty:
        print("No data found for the selected tickers in the year 2020.")
        return

    # 3. Create the plot
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(15, 8))

    # Draw the lines for each ticker using the new 'Normalized Price' column
    sns.lineplot(data=df_filtered, x='Date', y='Normalized Price', hue='Ticker', ax=ax, linewidth=2.5)

    # 4. Customize the plot's appearance
    ax.set_title('Normalized Stock Performance in 2020', fontsize=22, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=14, fontweight='bold')
    ax.set_ylabel('Normalized Price', fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', labelsize=12, rotation=45)
    ax.tick_params(axis='y', labelsize=12)
    ax.grid(True, which='major', linestyle='--', linewidth='0.5', color='grey')
    ax.axhline(100, color='grey', linestyle=':', linewidth=1.5)  # Add a line for the baseline

    legend = ax.legend(title='Ticker', fontsize=12, bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.setp(legend.get_title(), fontsize=14, fontweight='bold')

    plt.tight_layout()

    # 5. Save the plot to a file
    plt.savefig(output_png, dpi=300, bbox_inches='tight')
    print(f"Graph saved successfully to '{output_png}'")
    plt.show()


# --- Script Execution ---
if __name__ == '__main__':
    plot_normalized_price_increase_2020(
        prices_csv=STOCK_PRICES_FILE,
        tickers_to_plot=TICKERS_TO_PLOT,
        output_png=OUTPUT_PNG_FILE
    )