import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

PLOTS_DIR = "./output"

def create_plots_output_directory():
    """Ensure the plots output directory exists."""
    if not os.path.exists(PLOTS_DIR):
        os.makedirs(PLOTS_DIR)

def plot_full_network(G):
    """
    Draw the entire suspicious network with larger nodes and labels.
    Labels are offset so they do not cover the node circles.
    """
    H = G.copy()
    isolates = list(nx.isolates(H))
    H.remove_nodes_from(isolates)
    print(f"Removed {len(isolates)} isolated nodes for the suspicious full network map.")

    plt.figure(figsize=(28, 28))
    pos = nx.spring_layout(H, k=0.2, iterations=50, seed=42)

    communities = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    pagerank_scores = [float(H.nodes[n].get('pagerank_score', 0)) for n in H.nodes()]
    node_types = [H.nodes[n].get('type', 'transaction') for n in H.nodes()]

    politician_base_size = 800
    transaction_size = 120
    node_sizes = [
        politician_base_size + s * 120000 if t == 'politician' else transaction_size
        for s, t in zip(pagerank_scores, node_types)
    ]

    nx.draw_networkx_edges(H, pos, alpha=0.08, width=0.6)
    node_colors = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    cmap = plt.cm.get_cmap('viridis', max(communities) + 1)
    nx.draw_networkx_nodes(
        H, pos,
        node_color=node_colors, cmap=cmap,
        node_size=node_sizes, alpha=0.85
    )
    politician_nodes = [n for n, d in H.nodes(data=True) if d.get('type') == 'politician']
    labels = {n: n for n in politician_nodes}
    label_pos = {n: (pos[n][0], pos[n][1] + 0.035) for n in politician_nodes}  # upward offset

    nx.draw_networkx_labels(
        H, pos=label_pos, labels=labels,
        font_size=18, font_weight='bold',
        bbox=dict(facecolor='white', edgecolor='none', alpha=0.75, pad=0.6)
    )

    plt.title("Suspicious Politician Transaction Network Map", fontsize=30, fontweight="bold")
    plt.axis('off')

    output_path = os.path.join(PLOTS_DIR, "suspicious_full_network_map_large_text_offset.png")
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved larger-text suspicious full network map to {output_path}")

def plot_top_influencers(G):
    """
    Bar chart of the top 15 most suspicious influential politicians by PageRank.
    """
    politicians = {n: G.nodes[n] for n in G.nodes() if G.nodes[n].get('type') == 'politician'}
    if not politicians:
        print("No politician nodes found for influencer plot.")
        return

    df_data = {
        'Politician': list(politicians.keys()),
        'PageRank': [float(data.get('pagerank_score', 0)) for data in politicians.values()],
        'Community': [int(data.get('community_id', 0)) for data in politicians.values()]
    }
    df = pd.DataFrame(df_data).sort_values('PageRank', ascending=False).head(15)

    plt.figure(figsize=(14, 12))
    sns.barplot(x='PageRank', y='Politician', data=df, hue='Community', dodge=False, palette='viridis')
    plt.title("Top 15 Most Suspicious Influential Politicians (by PageRank)", fontsize=22, fontweight="bold")
    plt.xlabel("PageRank Score", fontsize=18)
    plt.ylabel("Politician", fontsize=18)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.legend(title='Community ID', fontsize=14, title_fontsize=16)
    plt.tight_layout()

    output_path = os.path.join(PLOTS_DIR, "top_influencers_large_text.png")
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Saved large-text top influencers plot to {output_path}")

if __name__ == '__main__':
    create_plots_output_directory()
    graph_path = "politician_network_analyzed.gexf"
    if not os.path.exists(graph_path):
        print(f"Error: Analyzed graph file not found at '{graph_path}'. Please run the analysis script first.")
    else:
        G = nx.read_gexf(graph_path)
        plot_full_network(G)
        plot_top_influencers(G)
        print(f"\nPlots have been generated in the '{PLOTS_DIR}' directory.")