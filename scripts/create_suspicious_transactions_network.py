# 1. Built-in modules
import os
from datetime import timedelta
from itertools import combinations
from datetime import timedelta

# 2. Third-party packages
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt


# 3. Internal company packages (none)

# 4. Current project modules (none)

def build_suspicious_transactions_network(
        csv_path: str,
        gexf_output_path: str,
        png_output_path: str
) -> nx.Graph:
    """Builds and saves a network graph of suspicious transactions.

    Args:
        csv_path: Path to the transactions CSV file.
        gexf_output_path: Path to save the GEXF graph file.
        png_output_path: Path to save the graph plot PNG.

    Returns:
        The constructed NetworkX graph.
    """
    df = pd.read_csv(csv_path)
    df["Traded_Date"] = pd.to_datetime(df["Traded_Date"])
    G = nx.Graph()

    for _, row in df.iterrows():
        politician_name = row["Name"]
        ticker = row["Ticker"]
        trade_date_str = row["Traded_Date"].strftime("%Y-%m-%d")
        transaction_id = f"{ticker}_{politician_name}_{trade_date_str}"

        G.add_node(politician_name, type="politician")

        if row.get("direct_legislative_connection", False) or row.get("subcommittee_decision", False):
            G.add_node(
                transaction_id,
                type="transaction",
                ticker=ticker,
                date=trade_date_str,
                suspicious=True
            )
            G.add_edge(politician_name, transaction_id)
        else:
            G.add_node(
                transaction_id,
                type="transaction",
                ticker=ticker,
                date=trade_date_str,
                suspicious=False
            )

    _add_transaction_edges(G)
    nx.write_gexf(G, gexf_output_path)
    _plot_and_save_graph(G, png_output_path)
    return G


def _add_transaction_edges(G: nx.Graph) -> None:
    """Adds edges between transaction nodes with the same ticker within 10 days.

    Only connects transactions if at least one of them is suspicious.
    Also ensures both transactions are connected to their respective politicians.
    """
    transaction_nodes = [
        node for node, attrs in G.nodes(data=True) if attrs.get("type") == "transaction"
    ]
    ticker_groups = {}
    for node_id in transaction_nodes:
        ticker = G.nodes[node_id]["ticker"]
        ticker_groups.setdefault(ticker, []).append(node_id)

    for nodes in ticker_groups.values():
        for u, v in combinations(nodes, 2):
            date1 = pd.to_datetime(G.nodes[u]["date"])
            date2 = pd.to_datetime(G.nodes[v]["date"])

            # Check if dates are within 10 days and at least one transaction is suspicious
            if (abs((date1 - date2).days) <= 10 and
                    (G.nodes[u].get("suspicious", False) or G.nodes[v].get("suspicious", False))):
                G.add_edge(u, v)
                # Ensure both transactions are connected to their politicians
                _ensure_politician_transaction_edges(G, u, v)


def _ensure_politician_transaction_edges(G: nx.Graph, transaction1: str, transaction2: str) -> None:
    """Ensures politician-transaction edges exist for connected transactions."""
    politician_nodes = [node for node, attrs in G.nodes(data=True) if attrs.get("type") == "politician"]

    for politician in politician_nodes:
        # Check if politician should be connected to either transaction
        if not G.has_edge(politician, transaction1):
            # Extract politician name from transaction ID format: ticker_politician_date
            transaction1_politician = transaction1.split('_')[1]
            if politician == transaction1_politician:
                G.add_edge(politician, transaction1)

        if not G.has_edge(politician, transaction2):
            transaction2_politician = transaction2.split('_')[1]
            if politician == transaction2_politician:
                G.add_edge(politician, transaction2)


def _plot_and_save_graph(G: nx.Graph, png_output_path: str) -> None:
    """Plots the network graph and saves it as a PNG file."""
    # Find politicians with outgoing edges to transactions
    politician_nodes = {node for node, attrs in G.nodes(data=True) if attrs.get("type") == "politician"}
    connected_nodes = set()

    for politician in politician_nodes:
        neighbors = list(G.neighbors(politician))
        if neighbors:  # Only include politicians with connections
            connected_nodes.add(politician)
            connected_nodes.update(neighbors)

    # Also include transaction nodes that have edges to other transactions
    transaction_nodes = {node for node, attrs in G.nodes(data=True) if attrs.get("type") == "transaction"}
    for transaction in transaction_nodes:
        if G.degree(transaction) > 0:  # Only include transactions with edges
            connected_nodes.add(transaction)

    # Create subgraph with only connected nodes
    G_filtered = G.subgraph(connected_nodes).copy()

    if G_filtered.number_of_nodes() == 0:
        print("No connected nodes to plot.")
        return

    plt.figure(figsize=(25, 25))
    node_colors = []
    node_sizes = []
    labels = {}

    for node, attrs in G_filtered.nodes(data=True):
        if attrs.get("type") == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300)
            labels[node] = node
        elif attrs.get("type") == "transaction":
            if attrs.get("suspicious", False):
                node_colors.append("red")
            else:
                node_colors.append("purple")
            node_sizes.append(50)
            labels[node] = ""
        else:
            node_colors.append("gray")
            node_sizes.append(50)
            labels[node] = ""

    pos = nx.spring_layout(G_filtered, iterations=100, seed=42)
    nx.draw_networkx_edges(G_filtered, pos, alpha=0.2)
    nx.draw_networkx_nodes(G_filtered, pos, node_color=node_colors, node_size=node_sizes)
    nx.draw_networkx_labels(G_filtered, pos, labels=labels, font_size=8, font_color="black")

    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='skyblue',
                   markersize=15, label='Politicians'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
                   markersize=10, label='Suspicious transactions'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='purple',
                   markersize=10,
                   label='Transactions made in same 10 days with other same ticker suspicious transaction')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)

    plt.title("Suspicious Transactions Network", size=20)
    plt.savefig(png_output_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    csv_path = os.path.join(project_root, "outputs", "transactions_with_analysis.csv")
    gexf_output_path = os.path.join(project_root, "outputs", "suspicious_transactions_network.gexf")
    png_output_path = os.path.join(project_root, "outputs", "suspicious_transactions_network.png")

    if not os.path.exists(csv_path):
        print(f"Error: The file {csv_path} was not found.")
        return

    G = build_suspicious_transactions_network(
        csv_path=csv_path,
        gexf_output_path=gexf_output_path,
        png_output_path=png_output_path
    )
    print(f"Network graph saved to {gexf_output_path}")
    print(f"Graph visualization saved to {png_output_path}")
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")


if __name__ == "__main__":
    main()
