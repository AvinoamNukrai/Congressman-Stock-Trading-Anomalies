import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

STOCK_PRICES_FILE = 'stock_prices_summary.csv'

TICKERS_TO_PLOT = ['UNH', 'GOOG', 'BA', 'LMT', 'AMZN','JPM', 'MSFT']

OUTPUT_PNG_FILE = 'stock_price_performance_2020.png'

def plot_price_increase_2020(prices_csv, tickers_to_plot, output_png):
    """
    Creates and saves a line chart showing the stock price evolution
    for a given list of tickers, filtered for the year 2020.
    """
    try:
        df = pd.read_csv(prices_csv)
    except FileNotFoundError:
        print(f"Error: The file '{prices_csv}' was not found.")
        return

    df['Date'] = pd.to_datetime(df['Date'])

    df = df[df['Date'].dt.year == 2020]

    df_filtered = df[df['Ticker'].isin(tickers_to_plot)]

    if df_filtered.empty:
        print("No data found for the selected tickers in the year 2020.")
        return

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(15, 8))

    sns.lineplot(data=df_filtered, x='Date', y='Close', hue='Ticker', ax=ax, linewidth=2.5)

    ax.set_title('Stock Price Performance in 2020', fontsize=22, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=14, fontweight='bold')
    ax.set_ylabel('Adjusted Close Price (USD)', fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', labelsize=12, rotation=45)
    ax.tick_params(axis='y', labelsize=12)
    legend = ax.legend(title='Ticker', fontsize=12)
    plt.setp(legend.get_title(), fontsize=14, fontweight='bold')
    ax.grid(True, which='major', linestyle='--', linewidth='0.5', color='grey')

    plt.tight_layout()

    plt.savefig(output_png, dpi=300)
    print(f"Graph saved successfully to '{output_png}'")
    plt.show()


if __name__ == '__main__':
    plot_price_increase_2020(
        prices_csv=STOCK_PRICES_FILE,
        tickers_to_plot=TICKERS_TO_PLOT,
        output_png=OUTPUT_PNG_FILE
    )