import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from itertools import combinations


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

            if (abs((date1 - date2).days) <= 10 and
                    (G.nodes[u].get("suspicious", False) or G.nodes[v].get("suspicious", False))):
                G.add_edge(u, v)


def _plot_and_save_graph(G: nx.Graph, png_output_path: str) -> None:
    """Plots the network graph and saves it as a PNG file with more spacing."""
    politician_nodes = {n for n, d in G.nodes(data=True) if d.get("type") == "politician"}
    connected_nodes = set()

    for politician in politician_nodes:
        neighbors = list(G.neighbors(politician))
        if neighbors:
            connected_nodes.add(politician)
            connected_nodes.update(neighbors)

    transaction_nodes = {n for n, d in G.nodes(data=True) if d.get("type") == "transaction"}
    for transaction in transaction_nodes:
        if G.degree(transaction) > 0:
            connected_nodes.add(transaction)

    G_filtered = G.subgraph(connected_nodes).copy()
    if G_filtered.number_of_nodes() == 0:
        print("No connected nodes to plot.")
        return

    plt.figure(figsize=(40, 40))
    node_colors, node_sizes, labels = [], [], {}

    for node, attrs in G_filtered.nodes(data=True):
        if attrs.get("type") == "politician":
            node_colors.append("skyblue")
            node_sizes.append(3500)
            labels[node] = node
        elif attrs.get("type") == "transaction":
            node_colors.append("red" if attrs.get("suspicious", False) else "purple")
            node_sizes.append(900 if attrs.get("suspicious", False) else 600)
            labels[node] = ""
        else:
            node_colors.append("gray")
            node_sizes.append(400)
            labels[node] = ""

    pos = nx.spring_layout(G_filtered, k=1.5, iterations=200, seed=42)

    nx.draw_networkx_edges(G_filtered, pos, edge_color="#444444", alpha=0.5, width=1.2)

    nx.draw_networkx_nodes(G_filtered, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_labels(
        G_filtered, pos, labels=labels, font_size=20, font_weight="bold", font_color="black",
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1.0)
    )

    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='skyblue', markersize=20, label='Politicians'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=15,
                   label='Suspicious transactions'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='purple', markersize=15,
                   label='Other connected transactions'),
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=18)

    plt.title("Suspicious Politician Transactions Network", size=32)
    plt.savefig(png_output_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    # Note: os.path.abspath(__file__) might not work in all environments (like Jupyter)
    # Using a simpler relative path structure.
    # Assumes the script is run from the `suspicious_transactions_network` directory.
    project_root = ".."
    csv_path = os.path.join(project_root, "suspicious_transactions_network", "transactions_with_analysis.csv")

    # --- FIX IS HERE: Create the output directory before using it ---
    output_dir = '.'
    os.makedirs(output_dir, exist_ok=True)

    gexf_output_path = os.path.join(output_dir, "suspicious_transactions_network.gexf")
    png_output_path = os.path.join(output_dir, "suspicious_transactions_network.png")

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