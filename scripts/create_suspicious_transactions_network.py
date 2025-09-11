import pandas as pd
import networkx as nx
import os
from datetime import timedelta
from itertools import combinations
import matplotlib.pyplot as plt


def create_network_from_transactions():
    """
    Reads the transactions CSV file, creates a network of politicians and transactions,
    and saves the graph to a GEXF file.

    the graph construction involves the following:
    - Nodes represent politicians (labeled as 'politician') and individual transactions (labeled as 'transaction' with attributes for ticker and date).
    - Edges between politicians and transactions are added only if the transaction was made by a politician who has a direct legislative connection to the relevant committee or if the transaction follows a subcommittee decision.
    - Additionally, edges are created between transactions of the same ticker that occurred within a 10-day interval.
    """
    # Construct the absolute path to the CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    csv_path = os.path.join(project_root, "outputs", "transactions_with_analysis.csv")
    output_path = os.path.join(
        project_root, "outputs", "suspicious_transactions_network.gexf"
    )
    png_output_path = os.path.join(
        project_root, "outputs", "suspicious_transactions_network.png"
    )

    # Check if the CSV file exists
    if not os.path.exists(csv_path):
        print(f"Error: The file {csv_path} was not found.")
        return

    # Read the CSV file
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading the CSV file: {e}")
        return

    # Create a new graph
    G = nx.Graph()

    # Convert 'Traded_Date' to datetime objects
    df["Traded_Date"] = pd.to_datetime(df["Traded_Date"])

    # Iterate over each transaction in the DataFrame
    for index, row in df.iterrows():
        politician_name = row["Name"]
        ticker = row["Ticker"]
        # Format date back to string for node ID
        trade_date_str = row["Traded_Date"].strftime("%Y-%m-%d")

        # Create a unique identifier for the transaction
        transaction_id = f"{ticker}_{politician_name}_{trade_date_str}"

        # Add nodes for the politician and the transaction
        G.add_node(politician_name, type="politician")
        G.add_node(
            transaction_id, type="transaction", ticker=ticker, date=trade_date_str
        )

        # Check for a connection based on the boolean flags
        direct_connection = row.get("direct_legislative_connection", False)
        subcommittee_decision = row.get("subcommittee_decision", False)

        if direct_connection or subcommittee_decision:
            G.add_edge(politician_name, transaction_id)

    # Add edges between transactions of the same ticker within 10 days
    transaction_nodes = [
        node for node, attrs in G.nodes(data=True) if attrs.get("type") == "transaction"
    ]

    # Group transaction nodes by ticker
    ticker_groups = {}
    for node_id in transaction_nodes:
        ticker = G.nodes[node_id]["ticker"]
        if ticker not in ticker_groups:
            ticker_groups[ticker] = []
        ticker_groups[ticker].append(node_id)

    for ticker, nodes in ticker_groups.items():
        for u, v in combinations(nodes, 2):
            date1_str = G.nodes[u]["date"]
            date2_str = G.nodes[v]["date"]

            date1 = pd.to_datetime(date1_str)
            date2 = pd.to_datetime(date2_str)

            if abs((date1 - date2).days) <= 10:
                G.add_edge(u, v)

    # Save the graph to a GEXF file
    nx.write_gexf(G, output_path)
    print(f"Network graph saved to {output_path}")
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")

    # Plot and save the graph as a PNG file
    plt.figure(figsize=(25, 25))

    node_colors = []
    node_sizes = []
    labels = {}
    for node, attrs in G.nodes(data=True):
        if attrs.get("type") == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300)
            labels[node] = node  # Label for politicians
        elif attrs.get("type") == "transaction":
            node_colors.append("tomato")
            node_sizes.append(50)
            labels[node] = ""  # No label for transactions
        else:
            node_colors.append("gray")
            node_sizes.append(50)
            labels[node] = ""

    pos = nx.spring_layout(G, iterations=100, seed=42)
    nx.draw_networkx_edges(G, pos, alpha=0.2)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_color="black")

    plt.title("Suspicious Transactions Network", size=20)
    plt.savefig(png_output_path, dpi=300)
    print(f"Graph visualization saved to {png_output_path}")


if __name__ == "__main__":
    create_network_from_transactions()
