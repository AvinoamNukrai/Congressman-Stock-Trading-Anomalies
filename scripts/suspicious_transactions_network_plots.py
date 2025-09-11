import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

PLOTS_DIR = "outputs/suspicious_transactions_analysis_plots"

def create_plots_output_directory():
    """Ensures the plots output directory exists."""
    if not os.path.exists(PLOTS_DIR):
        os.makedirs(PLOTS_DIR)

def plot_full_network(G):
    """
    Generates and saves a visualization of the entire network, colored by community
    and sized by PageRank.
    """
    # Create a copy and remove isolated nodes for a cleaner plot
    H = G.copy()
    isolates = list(nx.isolates(H))
    H.remove_nodes_from(isolates)
    print(f"Removed {len(isolates)} isolated nodes for the full network map.")

    plt.figure(figsize=(22, 22))
    
    # Use a layout that spreads out nodes for better visibility
    pos = nx.spring_layout(H, k=0.2, iterations=50, seed=42)
    
    # Get node attributes and ensure correct types
    communities = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    pagerank_scores = [float(H.nodes[n].get('pagerank_score', 0)) for n in H.nodes()]
    node_types = [H.nodes[n].get('type', 'transaction') for n in H.nodes()]

    # Differentiate sizes: make politicians much larger
    politician_base_size = 200
    transaction_size = 25
    node_sizes = [politician_base_size + s * 50000 if t == 'politician' else transaction_size for s, t in zip(pagerank_scores, node_types)]
    
    # Draw the graph
    # Draw edges first
    nx.draw_networkx_edges(H, pos, alpha=0.05)
    
    # Draw politician and transaction nodes separately to control their appearance
    politician_nodes = [n for n, d in H.nodes(data=True) if d.get('type') == 'politician']
    
    # Get community colors for all nodes
    node_colors = [int(H.nodes[n].get('community_id', 0)) for n in H.nodes()]
    cmap = plt.cm.get_cmap('viridis', max(communities) + 1)

    nodes = nx.draw_networkx_nodes(H, pos, node_color=node_colors, cmap=cmap, node_size=node_sizes, alpha=0.8)
    
    # Add labels only for politicians
    labels = {n: n for n in politician_nodes}
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=9, font_weight='bold', bbox=dict(facecolor='white', edgecolor='none', alpha=0.6))
    
    plt.title("Politician Transaction Network Map", fontsize=24)
    cbar = plt.colorbar(nodes, label='Community ID', ticks=range(max(communities) + 1))
    cbar.ax.tick_params(labelsize=12)
    cbar.set_label('Community ID', size=14)
    plt.axis('off')
    
    output_path = os.path.join(PLOTS_DIR, "full_network_map.png")
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"Saved full network map to {output_path}")

def plot_top_influencers(G):
    """
    Generates and saves a bar chart of the top 15 most influential politicians.
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
    
    plt.figure(figsize=(12, 10))
    sns.barplot(x='PageRank', y='Politician', data=df, hue='Community', dodge=False, palette='viridis')
    
    plt.title("Top 15 Most Influential Politicians (by PageRank)", fontsize=16)
    plt.xlabel("PageRank Score", fontsize=12)
    plt.ylabel("Politician", fontsize=12)
    plt.legend(title='Community ID')
    plt.tight_layout()
    
    output_path = os.path.join(PLOTS_DIR, "top_influencers.png")
    plt.savefig(output_path)
    plt.close()
    print(f"Saved top influencers plot to {output_path}")

if __name__ == '__main__':
    create_plots_output_directory()
    
    graph_path = "outputs/politician_network_analyzed.gexf"
    if not os.path.exists(graph_path):
        print(f"Error: Analyzed graph file not found at '{graph_path}'.")
        print("Please run the analysis script first.")
    else:
        G = nx.read_gexf(graph_path)
        
        # Generate the requested plots
        plot_full_network(G)
        plot_top_influencers(G)
        
        print(f"\nRequested plots have been generated in the '{PLOTS_DIR}' directory.")
