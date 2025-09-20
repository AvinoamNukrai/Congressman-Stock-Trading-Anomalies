import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import ast
import os

OUTPUTS_DIR = "."
TRANSACTIONS_CSV = os.path.join(OUTPUTS_DIR, "transactions_with_analysis.csv")
PROFILES_CSV = os.path.join(OUTPUTS_DIR, "politician_profiles.csv")
TOP_GRAPH_PNG = os.path.join(OUTPUTS_DIR, "top_sponsorship_companies.png")
TOP_N_COMPANIES = 7  # You can change how many top companies to display


def plot_top_companies(graph, company_scores, top_n, output_path):
    """
    Draws a network of the top N companies and their connected suspicious politicians,
    with a heatmap effect for dominance.
    """
    if not company_scores:
        print("No suspicious companies to plot.")
        return

    top_companies = sorted(company_scores, key=company_scores.get, reverse=True)[:top_n]

    connected_politicians = set()
    for company in top_companies:
        connected_politicians.update(graph.neighbors(company))

    nodes_to_keep = set(top_companies) | connected_politicians
    subgraph = graph.subgraph(nodes_to_keep).copy()

    fig, ax = plt.subplots(figsize=(18, 18))
    pos = nx.spring_layout(subgraph, k=0.5, iterations=60, seed=42)

    node_colors = []
    node_sizes = []
    labels = {}

    company_degrees = {c: subgraph.degree(c) for c in top_companies}
    max_degree = max(company_degrees.values()) if company_degrees else 1
    cmap = plt.cm.Reds

    for node, attrs in subgraph.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(600)
            labels[node] = node
        else:
            degree = company_degrees.get(node, 1)
            color = cmap(degree / max_degree)
            node_colors.append(color)
            node_sizes.append(2500 + degree * 100)
            labels[node] = node

    nx.draw_networkx_edges(subgraph, pos, ax=ax, alpha=0.5, edge_color="dimgray", width=1.2)
    nx.draw_networkx_nodes(subgraph, pos, ax=ax, node_color=node_colors, node_size=node_sizes, alpha=0.9)
    nx.draw_networkx_labels(subgraph, pos, ax=ax, labels=labels, font_size=14, font_weight="bold")

    ax.set_title(f"Top {top_n} Sponsorship Companies - Suspicious Politicians Only", fontsize=20)
    ax.axis("off")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max_degree))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.5)
    cbar.set_label("Number of Connected Politicians", fontsize=12)

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Top {top_n} companies graph saved to {output_path}")


def main():
    """
    Main function to build the sponsorship graph and generate the visualization.
    """
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    if not os.path.exists(TRANSACTIONS_CSV) or not os.path.exists(PROFILES_CSV):
        print(f"❌ Error: Required files not found. Ensure '{TRANSACTIONS_CSV}' and '{PROFILES_CSV}' exist.")
        return

    transactions = pd.read_csv(TRANSACTIONS_CSV)
    profiles = pd.read_csv(PROFILES_CSV)

    suspicious_counts = (
        transactions[transactions["direct_legislative_connection"] == True]
        .groupby("Name")
        .size()
        .to_dict()
    )

    graph = nx.Graph()
    for _, row in profiles.iterrows():
        name = row["politician_name"]
        try:
            sponsored_companies = ast.literal_eval(row["sponership_compaines_tickets"])
        except (ValueError, SyntaxError):
            sponsored_companies = []

        suspicious_trades = suspicious_counts.get(name, 0)

        if suspicious_trades > 0:
            graph.add_node(name, type="politician", suspicious=int(suspicious_trades))
            for company in sponsored_companies:
                graph.add_node(company, type="company")
                graph.add_edge(name, company, weight=suspicious_trades)

    pagerank_scores = nx.pagerank(graph, weight="weight")
    company_scores = {
        node: pagerank_scores[node]
        for node, data in graph.nodes(data=True)
        if data["type"] == "company"
    }

    plot_top_companies(
        graph=graph,
        company_scores=company_scores,
        top_n=TOP_N_COMPANIES,
        output_path=TOP_GRAPH_PNG
    )

if __name__ == "__main__":
    main()