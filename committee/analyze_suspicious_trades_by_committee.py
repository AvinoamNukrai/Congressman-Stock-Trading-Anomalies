import pandas as pd
import matplotlib.pyplot as plt
import ast
from collections import Counter
from matplotlib.ticker import MaxNLocator  # Import the necessary tool


def analyze_suspicious_trades_by_committee_vertical(committees_csv_path):
    """
    Analyzes and visualizes which congressional committees are most
    frequently associated with suspicious stock trades using a vertical bar chart.
    """
    try:
        df = pd.read_csv(committees_csv_path)
    except FileNotFoundError:
        print(f"Error: The file '{committees_csv_path}' was not found.")
        return

    suspicious_df = df[df['direct_legislative_connection'] == True].copy()
    print(f"Found {len(suspicious_df)} suspicious trades to analyze.")

    committee_counter = Counter()
    for index, row in suspicious_df.iterrows():
        try:
            committees_list = ast.literal_eval(row['subcommittees'])
            if isinstance(committees_list, list):
                committee_counter.update(committees_list)
        except (ValueError, SyntaxError):
            continue

    if not committee_counter:
        print("No committees found in the suspicious trades data.")
        return

    committee_counts_df = pd.DataFrame(committee_counter.items(), columns=['Committee', 'Count'])
    top_committees = committee_counts_df.sort_values(by='Count', ascending=False).head(15)

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(15, 10))

    top_committees.sort_values(by='Count', ascending=False).plot(
        kind='bar', x='Committee', y='Count', ax=ax,
        color='#3477a1', legend=False
    )

    ax.set_title('Top Congressional Committees by Suspicious Trading Activity', fontsize=22, fontweight='bold')
    ax.set_ylabel('Number of Associated Suspicious Trades', fontsize=14, fontweight='bold')
    ax.set_xlabel('Committee', fontsize=14, fontweight='bold')

    plt.xticks(rotation=45, ha='right')
    ax.tick_params(axis='x', labelsize=12)
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')

    ax.tick_params(axis='y', labelsize=12)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    for i in ax.patches:
        ax.text(i.get_x() + i.get_width() / 2, i.get_height() + 0.3, str(int(i.get_height())),
                fontsize=12, ha='center', va='bottom')

    plt.tight_layout()

    output_path = "committee_suspicious_trade_analysis.png"
    plt.savefig(output_path, dpi=300)
    print(f"Plot saved to '{output_path}'")

    plt.show()

COMMITTEES_FILE = 'committees.csv'
analyze_suspicious_trades_by_committee_vertical(COMMITTEES_FILE)