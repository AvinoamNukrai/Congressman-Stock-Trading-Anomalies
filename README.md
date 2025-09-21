# Congressman-Stock-Trading-Anomalies

Project Description:
This project analyzes U.S. congresspersons' stock trading behaviors to investigate two main
hypotheses: (1) that politicians exploit non-public information or their official positions for
personal financial gain through stock investments, and (2) that "circles" of politicians (e.g., by
party, office, or state) engage in coordinated stock trading. We aim to detect suspicious trading
patterns, identify clusters of individuals with similar financial behavior, and explore correlations
between trading activity and political affiliations or legislative events. Ultimately, this research
seeks to uncover instances of potential insider trading and hidden collaborative investment
networks.


Methodology:
To address these hypotheses, our methodology involves three core steps:
1. Construct Politician Networks: We will build graphs representing connections between
politicians based on shared committee memberships, co-sponsorships, and party
affiliations.
2. Identify Trading Communities: We will detect communities within these networks (or
across trading data) of politicians who traded the same stocks within specific timeframes.
3. Investigate Exploitation with LLMs & Scraping: For identified trading communities, we
will leverage LLMs (e.g., Perplexity AI) and web scraping to investigate if their
synchronized stock trades correlate with relevant legislative events, government contracts,
or policy changes, suggesting potential information exploitation.


Data Description:
Our primary dataset for congressional trading is the "Congressional Trading (Inception to March
23)" dataset from Kaggle. 


## Quickstart

Prerequisites:
- Python 3.10+
- A Kaggle account configured for `kagglehub` (optional if you already have local CSVs)

1) Create and activate a virtual environment
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2) Configure (optional)
- Copy `example_config.ini` to `config.ini` if you want to override defaults (model name, API key, filters).

3) Build transactions dataset with AI analysis (optional, uses Gemini if configured)
```
python create_transactions_table.py
```
This will produce `suspicious_transactions_network/transactions_with_analysis.csv` (or as configured).

4) Create suspicious transactions network (GEXF + PNG)
```
python suspicious_transactions_network/suspicious_transactions_network_creation.py
```
Outputs:
- `suspicious_transactions_network/suspicious_transactions_network.gexf`
- `suspicious_transactions_network/suspicious_transactions_network.png`

5) Analyze the network (communities + centrality) and generate plots
```
python suspicious_transactions_network/suspicious_transactions_network_analysis.py
python suspicious_transactions_network/suspicious_transactions_network_plots.py
```
Outputs:
- `suspicious_transactions_network/politician_network_analyzed.gexf`
- `suspicious_transactions_network/suspicious_full_network_map.png`
- `suspicious_transactions_network/suspicious_top_influencers.png`

6) Optional: Re-run plots only
```
python suspicious_transactions_network/suspicious_transactions_network_plots.py
```

Tips:
- If you already have `transactions_with_analysis.csv` in `suspicious_transactions_network/`, you can skip step 3.
- All outputs are written under `suspicious_transactions_network/` by default.
- To start fresh, you can delete generated files in `suspicious_transactions_network/`.

## Structure
- `create_transactions_table.py`: build filtered transactions and (optionally) enrich with AI analysis.
- `create_politician_table.py`: build politician profiles and pairwise collaboration tables (optional flow).
- `suspicious_transactions_network/`:
  - `suspicious_transactions_network_creation.py`: build the bipartite network from the transactions CSV.
  - `suspicious_transactions_network_analysis.py`: Louvain communities, PageRank, attributes on nodes.
  - `suspicious_transactions_network_plots.py`: full network map and top influencers plots.

## Troubleshooting
- Module not found (e.g., `networkx`): ensure the virtual environment is active and requirements are installed.
- File not found: run the creation step first so the expected CSV/GEXF files exist.
- Slow plotting: large graphs can be heavy; try reducing the date window or transactions per politician in the config.
