import networkx as nx
import community as community_louvain
from collections import Counter
from itertools import combinations

def analyze_network(graph_path="../outputs/suspicious_transactions_network.gexf"):
    """
    Analyzes a politician transaction network by creating a politician-only projected graph
    to identify communities, influential politicians, and suspicious trading patterns.

    Args:
        graph_path (str): The path to the GEXF file containing the full network graph.
    """
    try:
        G = nx.read_gexf(graph_path)
    except FileNotFoundError:
        print(f"Error: The file '{graph_path}' was not found.")
        return

    politician_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'politician']

    # --- 1. Create a Politician-Only Projected Graph ---
    G_politician = nx.Graph()
    G_politician.add_nodes_from(politician_nodes)

    for p1, p2 in combinations(politician_nodes, 2):
        # Find paths of length 2, 3, or 4 (Politician -> Tx -> ... -> Politician)
        for path in nx.all_simple_paths(G, source=p1, target=p2, cutoff=4):
            # Ensure the path is strictly Politician -> ... -> Politician
            if all(G.nodes[n].get('type') != 'politician' for n in path[1:-1]):
                if G_politician.has_edge(p1, p2):
                    G_politician[p1][p2]['weight'] += 1
                else:
                    G_politician.add_edge(p1, p2, weight=1)

    # --- 2. Analyze the Politician-Only Graph ---
    # Community Detection on the projected graph
    partition = community_louvain.best_partition(G_politician, weight='weight')

    # Centrality Analysis on the projected graph
    pagerank = nx.pagerank(G_politician, weight='weight')

    # --- 3. Update Original Graph with New Analysis ---
    nx.set_node_attributes(G, partition, 'community_id')
    nx.set_node_attributes(G, pagerank, 'pagerank_score')

    # --- 4. Reporting ---
    print("--- Politician Network Analysis Report ---")
    
    # Invert partition for easier lookup
    communities = {}
    for node, comm_id in partition.items():
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(node)

    for comm_id, politicians in communities.items():
        if not politicians:
            continue

        print(f"\n--- Community {comm_id} ---")
        print(f"Politician Members: {', '.join(politicians)}")

        # Centrality
        politician_pagerank = {p: pagerank.get(p, 0) for p in politicians}
        sorted_politicians = sorted(politician_pagerank.items(), key=lambda item: item[1], reverse=True)
        print("\nTop 3 Most Central Politicians in Community:")
        for i, (p, score) in enumerate(sorted_politicians[:3]):
            print(f"{i+1}. {p} (PageRank: {score:.4f})")

        # Path Detection (in the original graph)
        print("\nConnected Trading Paths (in original graph):")
        if len(politicians) > 1:
            path_found = False
            for p1, p2 in combinations(politicians, 2):
                try:
                    for path in nx.all_simple_paths(G, source=p1, target=p2, cutoff=4):
                         if all(G.nodes[n].get('type') != 'politician' for n in path[1:-1]):
                            print(f"  - {' -> '.join(path)}")
                            path_found = True
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue
            if not path_found:
                print("  - No direct trading paths found between members in the original graph.")
        else:
            print("  - No paths to detect (only one politician in this community).")

        # Frequent Pattern Mining
        community_tickers = []
        for p in politicians:
            for neighbor in G.neighbors(p):
                if G.nodes[neighbor].get('type') == 'transaction':
                    ticker = G.nodes[neighbor].get('ticker')
                    if ticker:
                        community_tickers.append(ticker)
        
        if community_tickers:
            print("\nFrequent Tickers in Community:")
            ticker_counts = Counter(community_tickers)
            print("  Top 5 Single Tickers:")
            for ticker, count in ticker_counts.most_common(5):
                print(f"    - {ticker}: {count} times")

            pair_counts = Counter()
            for p in politicians:
                p_tickers = set()
                for neighbor in G.neighbors(p):
                    if G.nodes[neighbor].get('type') == 'transaction':
                        ticker = G.nodes[neighbor].get('ticker')
                        if ticker:
                            p_tickers.add(ticker)
                for pair in combinations(sorted(list(p_tickers)), 2):
                    pair_counts[pair] += 1
            
            if pair_counts:
                print("\n  Top 3 Co-Traded Ticker Pairs:")
                for pair, count in pair_counts.most_common(3):
                    print(f"    - {pair[0]}-{pair[1]}: {count} times")

    # --- 5. Save the updated graph ---
    output_path = "../outputs/politician_network_analyzed.gexf"
    # Make sure all attributes are strings for GEXF compatibility
    for node, data in G.nodes(data=True):
        for key, value in data.items():
            G.nodes[node][key] = str(value)
            
    nx.write_gexf(G, output_path)
    print(f"\nSuccessfully saved analyzed graph to '{output_path}'")

if __name__ == '__main__':
    analyze_network()