import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import ast
import os

OUTPUTS_DIR = "../outputs"

def build_sponsorship_graph_all(
    profiles_csv,
    gexf_output,
    pagerank_csv,
    network_png,
    top_graph_png,
    bar_png,
    summary_csv,
    top_n=7
):
    """
    Build a bipartite graph (politicians <-> sponsored companies),
    include all politicians (not just suspicious),
    compute PageRank for companies, and export results.
    """
    profiles = pd.read_csv(profiles_csv)

    G = nx.Graph()

    for _, row in profiles.iterrows():
        name = row["politician_name"]
        try:
            sponsored_companies = ast.literal_eval(row["sponership_compaines_tickets"])
        except Exception:
            sponsored_companies = []

        # Add politician node
        G.add_node(name, type="politician")

        # Add edges to their sponsored companies
        for company in sponsored_companies:
            G.add_node(company, type="company")
            G.add_edge(name, company, weight=1)

    # Run PageRank
    pr = nx.pagerank(G, weight="weight")

    # Extract PageRank scores for companies only
    company_scores = {
        n: pr[n] for n, d in G.nodes(data=True) if d["type"] == "company"
    }

    # Save PageRank scores to CSV
    df_scores = pd.DataFrame(
        [{"Company": c, "PageRank": score} for c, score in company_scores.items()]
    ).sort_values("PageRank", ascending=False)
    df_scores.to_csv(pagerank_csv, index=False)

    # Build summary table: number of politicians per company
    summary_rows = []
    for company in company_scores.keys():
        neighbors = list(G.neighbors(company))
        summary_rows.append({
            "Company": company,
            "PoliticiansConnected": len(neighbors),
            "PageRank": company_scores[company]
        })
    df_summary = pd.DataFrame(summary_rows).sort_values("PageRank", ascending=False)
    df_summary.to_csv(summary_csv, index=False)

    # Save graph as GEXF (for Gephi)
    nx.write_gexf(G, gexf_output)

    # Draw full network
    plot_sponsorship_network(G, network_png, pr)

    # Draw top N companies with connected politicians
    plot_top_companies(G, company_scores, top_n=top_n, output_path=top_graph_png)

    # Draw bar chart for top N companies
    plot_top_companies_pagerank(df_summary, top_n=top_n, output_path=bar_png)

    return G, df_summary


def plot_sponsorship_network(G, output_path, pr_scores):
    """Draw the full bipartite network (politicians–companies) and save as PNG."""
    if G.number_of_nodes() == 0:
        print("No politician-company edges to plot.")
        return

    plt.figure(figsize=(22, 22))
    pos = nx.spring_layout(G, k=0.4, iterations=60, seed=42)

    node_colors, node_sizes, labels = [], [], {}
    for node, attrs in G.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300)
            labels[node] = node
        else:  # company
            node_colors.append("green")
            node_sizes.append(1200 + float(pr_scores.get(node, 0)) * 8000)
            labels[node] = node

    nx.draw_networkx_edges(G, pos, alpha=0.25)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.85)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight="bold")

    plt.title("Politician–Sponsorship Companies Network (All Trades)", fontsize=18)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Sponsorship network visualization saved to {output_path}")


def plot_top_companies(G, company_scores, top_n=7, output_path="outputs/top_sponsorship_companies.png"):
    """Draw a network of the top N companies and their connected politicians."""
    if not company_scores:
        print("No companies to plot.")
        return

    top_companies = [c for c, _ in sorted(company_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]]

    connected_politicians = set()
    for c in top_companies:
        connected_politicians.update(G.neighbors(c))

    nodes_to_keep = set(top_companies) | connected_politicians
    H = G.subgraph(nodes_to_keep).copy()

    plt.figure(figsize=(15, 15))
    pos = nx.spring_layout(H, k=0.4, iterations=50, seed=42)

    node_colors, node_sizes, labels = [], [], {}
    for node, attrs in H.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300)
            labels[node] = node
        else:  # company
            node_colors.append("green")
            node_sizes.append(1500)
            labels[node] = node

    nx.draw_networkx_edges(H, pos, alpha=0.3)
    nx.draw_networkx_nodes(H, pos, node_color=node_colors, node_size=node_sizes, alpha=0.85)
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=9, font_weight="bold")

    plt.title(f"Top {top_n} Sponsorship Companies (All Politicians)", fontsize=16)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Top {top_n} sponsorship companies visualization saved to {output_path}")


def plot_top_companies_pagerank(df_summary, top_n=7, output_path="outputs/top_sponsorship_companies_pagerank.png"):
    """Draw a horizontal bar chart of the top N companies by PageRank score."""
    df_sorted = df_summary.sort_values("PageRank", ascending=False).head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(df_sorted["Company"], df_sorted["PageRank"], color="green")
    plt.gca().invert_yaxis()

    plt.xlabel("PageRank Score")
    plt.ylabel("Company")
    plt.title(f"Top {top_n} Sponsorship Companies by PageRank (All Politicians)", fontsize=14, weight="bold")

    for i, (score) in enumerate(df_sorted["PageRank"]):
        plt.text(score, i, f"{score:.4f}", va="center", ha="left", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Top {top_n} sponsorship companies PageRank chart saved to {output_path}")


def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    profiles_csv = os.path.join(OUTPUTS_DIR, "politician_profiles.csv")
    gexf_output = os.path.join(OUTPUTS_DIR, "sponsorship_network_all.gexf")
    pagerank_csv = os.path.join(OUTPUTS_DIR, "sponsorship_pagerank_all.csv")
    network_png = os.path.join(OUTPUTS_DIR, "sponsorship_network_all.png")
    top_graph_png = os.path.join(OUTPUTS_DIR, "top_sponsorship_companies_all.png")
    bar_png = os.path.join(OUTPUTS_DIR, "top_sponsorship_companies_pagerank_all.png")
    summary_csv = os.path.join(OUTPUTS_DIR, "sponsorship_summary_all.csv")

    if not os.path.exists(profiles_csv):
        print("Error: Required CSV file not found in outputs/. Please run previous steps first.")
        return

    G, df_summary = build_sponsorship_graph_all(
        profiles_csv,
        gexf_output, pagerank_csv, network_png,
        top_graph_png, bar_png, summary_csv, top_n=7
    )

    print("Top 7 sponsorship companies by PageRank (all politicians):")
    print(df_summary.head(7))
    print(f"\nGraph saved to {gexf_output}")
    print(f"PageRank scores saved to {pagerank_csv}")
    print(f"Summary saved to {summary_csv}")
    print(f"PNG (full network) saved to {network_png}")
    print(f"PNG (top 7 companies) saved to {top_graph_png}")
    print(f"PNG (top 7 companies bar chart) saved to {bar_png}")
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")


if __name__ == "__main__":
    main()