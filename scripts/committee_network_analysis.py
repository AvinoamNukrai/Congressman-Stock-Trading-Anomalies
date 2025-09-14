import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import ast
import os

OUTPUTS_DIR = "../outputs"

def build_committee_graph(transactions_csv, profiles_csv, gexf_output, csv_output, png_output, top_png, top_bar_png, top_n=7):
    """
    Build a bipartite graph (politicians <-> committees), weight edges by suspicious trades,
    compute PageRank for committees, and export results.
    """
    # Read data
    transactions = pd.read_csv(transactions_csv)
    profiles = pd.read_csv(profiles_csv)

    # Count suspicious trades per politician
    suspicious_counts = (
        transactions[transactions["direct_legislative_connection"] == True]
        .groupby("Name")
        .size()
        .to_dict()
    )

    G = nx.Graph()

    for _, row in profiles.iterrows():
        name = row["politician_name"]
        committees = ast.literal_eval(row["116_congress_committees"])
        suspicious_trades = suspicious_counts.get(name, 0)

        # Add politician node
        G.add_node(name, type="politician", suspicious=int(suspicious_trades))

        # Add edges to committees
        for committee in committees:
            G.add_node(committee, type="committee")
            G.add_edge(name, committee, weight=suspicious_trades)

    # Run PageRank
    pr = nx.pagerank(G, weight="weight")

    # Committee scores only
    committee_scores = {
        n: pr[n] for n, d in G.nodes(data=True) if d["type"] == "committee"
    }

    # Save to CSV
    df_scores = pd.DataFrame(
        [{"committee": c, "pagerank": score} for c, score in committee_scores.items()]
    ).sort_values("pagerank", ascending=False)
    df_scores.to_csv(csv_output, index=False)

    # Save graph as GEXF (can be opened in Gephi)
    nx.write_gexf(G, gexf_output)

    # Draw full network graph
    plot_committee_network(G, png_output, pr)

    # Draw top N committees (with politicians)
    plot_top_committees(G, committee_scores, top_n=top_n, output_path=top_png)

    # Draw bar chart of top N committees by PageRank
    plot_top_committees_pagerank(df_scores, top_n=top_n, output_path=top_bar_png)

    return G, df_scores


def plot_committee_network(G, output_path, pr_scores):
    """Draw the full graph and save as PNG"""
    plt.figure(figsize=(22, 22))
    pos = nx.spring_layout(G, k=0.35, iterations=60, seed=42)

    node_colors = []
    node_sizes = []
    labels = {}

    for node, attrs in G.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300 + attrs.get("suspicious", 0) * 50)
            labels[node] = node
        else:  # committee
            node_colors.append("orange")
            node_sizes.append(1200 + float(pr_scores.get(node, 0)) * 8000)
            labels[node] = node

    nx.draw_networkx_edges(G, pos, alpha=0.2)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8, font_weight="bold")

    plt.title("Committee–Politician Network (Suspicious Trades Weighted)", fontsize=18)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Committee network visualization saved to {output_path}")


def plot_top_committees(G, committee_scores, top_n=7, output_path="outputs/top_committees.png"):
    """Draw only the top N committees with their connected politicians"""
    top_committees = [c for c, _ in sorted(committee_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]]

    connected_politicians = set()
    for c in top_committees:
        connected_politicians.update(G.neighbors(c))

    nodes_to_keep = set(top_committees) | connected_politicians
    H = G.subgraph(nodes_to_keep).copy()

    plt.figure(figsize=(15, 15))
    pos = nx.spring_layout(H, k=0.4, iterations=50, seed=42)

    node_colors = []
    node_sizes = []
    labels = {}

    for node, attrs in H.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300 + attrs.get("suspicious", 0) * 50)
            labels[node] = node
        else:  # committee
            node_colors.append("orange")
            node_sizes.append(1500)
            labels[node] = node

    nx.draw_networkx_edges(H, pos, alpha=0.3)
    nx.draw_networkx_nodes(H, pos, node_color=node_colors, node_size=node_sizes, alpha=0.85)
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=9, font_weight="bold")

    plt.title(f"Top {top_n} Committees and Connected Politicians", fontsize=16)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Top {top_n} committees visualization saved to {output_path}")


def plot_top_committees_pagerank(df_scores, top_n=7, output_path="outputs/top_committees_pagerank.png"):
    """Draw a horizontal bar chart of the top N committees by PageRank"""
    df_sorted = df_scores.sort_values("pagerank", ascending=False).head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(df_sorted["committee"], df_sorted["pagerank"], color="orange")
    plt.gca().invert_yaxis()  # top committee appears first

    plt.xlabel("PageRank Score", fontsize=12)
    plt.ylabel("Committee", fontsize=12)
    plt.title(f"Top {top_n} Committees by PageRank", fontsize=14, weight="bold")

    for i, (score) in enumerate(df_sorted["pagerank"]):
        plt.text(score, i, f"{score:.4f}", va="center", ha="left", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Top {top_n} committees PageRank chart saved to {output_path}")


def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    transactions_csv = os.path.join(OUTPUTS_DIR, "transactions_with_analysis.csv")
    profiles_csv = os.path.join(OUTPUTS_DIR, "politician_profiles.csv")
    gexf_output = os.path.join(OUTPUTS_DIR, "committee_network.gexf")
    csv_output = os.path.join(OUTPUTS_DIR, "committee_pagerank.csv")
    png_output = os.path.join(OUTPUTS_DIR, "committee_network.png")
    top_png = os.path.join(OUTPUTS_DIR, "top_committees.png")
    top_bar_png = os.path.join(OUTPUTS_DIR, "top_committees_pagerank.png")

    if not os.path.exists(transactions_csv) or not os.path.exists(profiles_csv):
        print("Error: Required CSV files not found in outputs/. Please run previous steps first.")
        return

    G, df_scores = build_committee_graph(
        transactions_csv, profiles_csv, gexf_output, csv_output, png_output, top_png, top_bar_png, top_n=7
    )

    print("Top 7 committees by PageRank:")
    print(df_scores.head(7))
    print(f"\nGraph saved to {gexf_output}")
    print(f"Scores saved to {csv_output}")
    print(f"PNG (full network) saved to {png_output}")
    print(f"PNG (top 7 committees) saved to {top_png}")
    print(f"PNG (top 7 committees bar chart) saved to {top_bar_png}")
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")


if __name__ == "__main__":
    main()