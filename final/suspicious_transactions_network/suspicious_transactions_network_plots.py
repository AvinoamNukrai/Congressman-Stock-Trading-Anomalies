import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

PLOTS_DIR = "."


def create_plots_output_directory():
    """Ensures the plots output directory exists."""
    if not os.path.exists(PLOTS_DIR):
        os.makedirs(PLOTS_DIR)


def plot_full_network(G):
    """
    Generates and saves a visualization of the entire suspicious network,
    colored by community and sized by PageRank.
    """
    H = G.copy()

    if "Mark Green" in H.nodes:
        H.remove_node("Mark Green")

    isolates = list(nx.isolates(H))
    H.remove_nodes_from(isolates)
    print(f"Removed {len(isolates)} isolated nodes for the suspicious full network map.")

    plt.figure(figsize=(22, 22))
    pos = nx.spring_layout(H, k=0.2, iterations=50, seed=42)

    communities = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    pagerank_scores = [float(H.nodes[n].get('pagerank_score', 0)) for n in H.nodes()]
    node_types = [H.nodes[n].get('type', 'transaction') for n in H.nodes()]

    politician_base_size = 200
    transaction_size = 25
    node_sizes = [
        politician_base_size + s * 50000 if t == 'politician' else transaction_size
        for s, t in zip(pagerank_scores, node_types)
    ]

    nx.draw_networkx_edges(H, pos, alpha=0.6, edge_color='black', width=0.5)

    politician_nodes = [n for n, d in H.nodes(data=True) if d.get('type') == 'politician']
    node_colors = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    cmap = plt.cm.get_cmap('viridis', max(communities) + 1)

    nx.draw_networkx_nodes(H, pos, node_color=node_colors, cmap=cmap,
                           node_size=node_sizes, alpha=0.8)

    labels = {n: n for n in politician_nodes}
    label_pos = {k: (v[0], v[1] + 0.035) for k, v in pos.items()}

    # --- TEXT BIGGER, BOLDER, AND WITH BACKGROUND ---
    nx.draw_networkx_labels(H, label_pos, labels=labels, font_size=16,
                            font_weight='bold',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))

    plt.title("Suspicious Politician Transaction Network Map", fontsize=28, fontweight='bold')
    plt.axis('off')

    output_path = os.path.join(PLOTS_DIR, "suspicious_full_network_map.png")
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved suspicious full network map to {output_path}")


def plot_top_influencers(G):
    """
    Generates and saves a bar chart of the top 15 most suspicious influential politicians.
    """
    politicians = {
        n: G.nodes[n] for n in G.nodes()
        if G.nodes[n].get('type') == 'politician' and n != "Mark Green"
    }

    if not politicians:
        print("No politician nodes found for influencer plot.")
        return

    df_data = {
        'Politician': list(politicians.keys()),
        'PageRank': [float(data.get('pagerank_score', 0)) for data in politicians.values()],
        'Community': [int(data.get('community_id', 0)) for data in politicians.values()]
    }

    df = pd.DataFrame(df_data).sort_values('PageRank', ascending=False).head(15)

    plt.figure(figsize=(12, 10))
    sns.barplot(x='PageRank', y='Politician', data=df, hue='Community',
                dodge=False, palette='viridis')

    # --- TEXT BIGGER & BOLDER ---
    plt.title("Top Most Suspicious Influential Politicians", fontsize=20, fontweight='bold')
    plt.xlabel("PageRank Score", fontsize=14, fontweight='bold')
    plt.ylabel("Politician", fontsize=14, fontweight='bold')

    # Increase tick label size for readability
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)

    legend = plt.legend(title='Community ID', fontsize=12)
    plt.setp(legend.get_title(), fontsize=14, fontweight='bold')

    plt.tight_layout()

    output_path = os.path.join(PLOTS_DIR, "suspicious_top_influencers.png")
    plt.savefig(output_path)
    plt.close()
    print(f"Saved suspicious top influencers plot to {output_path}")


if __name__ == '__main__':
    create_plots_output_directory()

    graph_path = "politician_network_analyzed.gexf"
    if not os.path.exists(graph_path):
        print(f"Error: Analyzed graph file not found at '{graph_path}'.")
        print("Please run the analysis script first.")
    else:
        G = nx.read_gexf(graph_path)

        plot_full_network(G)
        plot_top_influencers(G)

        print(f"\nSuspicious plots have been generated in the '{PLOTS_DIR}' directory.")