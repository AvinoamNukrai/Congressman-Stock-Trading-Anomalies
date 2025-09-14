import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import ast
import os

OUTPUTS_DIR = "../outputs"

def build_sponsorship_graph(
    transactions_csv,
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
    include only politicians with ≥1 suspicious trade,
    compute PageRank for companies, and export results.
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
        try:
            sponsored_companies = ast.literal_eval(row["sponership_compaines_tickets"])
        except Exception:
            sponsored_companies = []
        suspicious_trades = suspicious_counts.get(name, 0)

        # Add politician node only if they have at least one suspicious trade
        if suspicious_trades > 0:
            G.add_node(name, type="politician", suspicious=int(suspicious_trades))

            # Add edges to their sponsored companies
            for company in sponsored_companies:
                G.add_node(company, type="company")
                G.add_edge(name, company, weight=suspicious_trades)

    # Run PageRank on the full graph
    pr = nx.pagerank(G, weight="weight")

    # Extract PageRank scores for companies only
    company_scores = {
        n: pr[n] for n, d in G.nodes(data=True) if d["type"] == "company"
    }

    # Save company PageRank scores to CSV
    df_scores = pd.DataFrame(
        [{"company": c, "pagerank": score} for c, score in company_scores.items()]
    ).sort_values("pagerank", ascending=False)
    df_scores.to_csv(pagerank_csv, index=False)

    # Build a summary table: number of politicians with suspicious trades per company
    summary_rows = []
    for company in company_scores.keys():
        neighbors = list(G.neighbors(company))
        suspicious_politicians = sum(
            G.nodes[n].get("suspicious", 0) > 0
            for n in neighbors if G.nodes[n]["type"] == "politician"
        )
        summary_rows.append({
            "company": company,
            "connected_politicians": len(neighbors),
            "suspicious_politicians": suspicious_politicians,
            "pagerank": company_scores[company]
        })
    df_summary = pd.DataFrame(summary_rows).sort_values("pagerank", ascending=False)
    df_summary.to_csv(summary_csv, index=False)

    # Save graph as GEXF (for Gephi)
    nx.write_gexf(G, gexf_output)

    # Draw full network graph (politicians <-> companies)
    plot_sponsorship_network(G, network_png, pr)

    # Draw top N companies with connected suspicious politicians
    plot_top_companies(G, company_scores, top_n=top_n, output_path=top_graph_png)

    # Draw horizontal bar chart of top N companies by PageRank
    plot_top_companies_pagerank(df_summary, top_n=top_n, output_path=bar_png)

    return G, df_summary


def plot_sponsorship_network(G, output_path, pr_scores):
    """Draw the full bipartite network (politicians–companies) and save as PNG."""
    if G.number_of_nodes() == 0:
        print("No suspicious politician-company edges to plot.")
        return

    plt.figure(figsize=(22, 22))
    pos = nx.spring_layout(G, k=0.4, iterations=60, seed=42)

    node_colors = []
    node_sizes = []
    labels = {}

    for node, attrs in G.nodes(data=True):
        if attrs["type"] == "politician":
            node_colors.append("skyblue")
            node_sizes.append(300 + attrs.get("suspicious", 0) * 50)
            labels[node] = node
        else:  # company node
            node_colors.append("green")
            node_sizes.append(1200 + float(pr_scores.get(node, 0)) * 8000)
            labels[node] = node

    nx.draw_networkx_edges(G, pos, alpha=0.25)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.85)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight="bold")

    plt.title("Politician–Sponsorship Companies Network (Suspicious Only)", fontsize=18)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Sponsorship network visualization saved to {output_path}")


def plot_top_companies(G, company_scores, top_n=7, output_path="outputs/top_sponsorship_companies.png"):
    """Draw a network of the top N companies and their connected suspicious politicians."""
    if not company_scores:
        print("No suspicious companies to plot.")
        return

    top_companies = [c for c, _ in sorted(company_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]]

    connected_politicians = set()
    for c in top_companies:
        connected_politicians.update(G.neighbors(c))

    nodes_to_keep = set(top_companies) | connected_politicians
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
        else:  # company node
            node_colors.append("green")
            node_sizes.append(1500)
            labels[node] = node

    nx.draw_networkx_edges(H, pos, alpha=0.3)
    nx.draw_networkx_nodes(H, pos, node_color=node_colors, node_size=node_sizes, alpha=0.85)
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=9, font_weight="bold")

    plt.title(f"Top {top_n} Sponsorship Companies (Suspicious Politicians Only)", fontsize=16)
    plt.axis("off")
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Top {top_n} suspicious sponsorship companies visualization saved to {output_path}")


def plot_top_companies_pagerank(df_summary, top_n=7, output_path="outputs/top_sponsorship_companies_pagerank.png"):
    """Draw a horizontal bar chart of the top N companies by PageRank score."""
    df_sorted = df_summary.sort_values("pagerank", ascending=False).head(top_n)

    plt.figure(figsize=(10, 6))
    plt.barh(df_sorted["company"], df_sorted["pagerank"], color="green")
    plt.gca().invert_yaxis()

    plt.xlabel("PageRank Score", fontsize=12)
    plt.ylabel("Company", fontsize=12)
    plt.title(f"Top {top_n} Sponsorship Companies by PageRank (Suspicious Politicians)", fontsize=14, weight="bold")

    for i, (score) in enumerate(df_sorted["pagerank"]):
        plt.text(score, i, f"{score:.4f}", va="center", ha="left", fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Top {top_n} sponsorship companies PageRank chart saved to {output_path}")


def main():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    transactions_csv = os.path.join(OUTPUTS_DIR, "transactions_with_analysis.csv")
    profiles_csv = os.path.join(OUTPUTS_DIR, "politician_profiles.csv")
    gexf_output = os.path.join(OUTPUTS_DIR, "sponsorship_network.gexf")
    pagerank_csv = os.path.join(OUTPUTS_DIR, "sponsorship_pagerank.csv")
    network_png = os.path.join(OUTPUTS_DIR, "sponsorship_network.png")
    top_graph_png = os.path.join(OUTPUTS_DIR, "top_sponsorship_companies.png")
    bar_png = os.path.join(OUTPUTS_DIR, "top_sponsorship_companies_pagerank.png")
    summary_csv = os.path.join(OUTPUTS_DIR, "sponsorship_summary.csv")

    if not os.path.exists(transactions_csv) or not os.path.exists(profiles_csv):
        print("Error: Required CSV files not found in outputs/. Please run previous steps first.")
        return

    G, df_summary = build_sponsorship_graph(
        transactions_csv, profiles_csv,
        gexf_output, pagerank_csv, network_png,
        top_graph_png, bar_png, summary_csv, top_n=7
    )

    print("Top 7 suspicious sponsorship companies by PageRank:")
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