# Congressman-Stock-Trading-Anomalies
Project Description
This project analyzes U.S. congresspersons' stock trading behaviors to investigate two main
hypotheses: (1) that politicians exploit non-public information or their official positions for
personal financial gain through stock investments, and (2) that "circles" of politicians (e.g., by
party, office, or state) engage in coordinated stock trading. We aim to detect suspicious trading
patterns, identify clusters of individuals with similar financial behavior, and explore correlations
between trading activity and political affiliations or legislative events. Ultimately, this research
seeks to uncover instances of potential insider trading and hidden collaborative investment
networks.


Methodology
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


Data Description
Our primary dataset for congressional trading is the "Congressional Trading (Inception to March
23)" dataset from Kaggle. 
