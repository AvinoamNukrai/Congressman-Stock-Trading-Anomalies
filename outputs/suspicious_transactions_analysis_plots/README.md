# Explanation of the Network Analysis Plots

This file explains the visualizations generated from the analysis of the politician transaction network.

---

### 1. `full_network_map.png`

**What it is:** This image is a "map" of the entire suspicious transaction network. It is designed to give a bird's-eye view of trading activity and the relationships between politicians.

**How to Read the Map:**

*   **Nodes (The Dots and Circles):**
    *   **Large, Labeled Circles:** Each of these represents a **politician**.
    *   **Small Dots:** Each small dot represents a single **stock transaction** that connects the politicians.

*   **Lines (The Connections):**
    *   The faint gray lines show the connections. A line from a politician to a small dot means they executed that trade. A line between two dots means they are for the same stock and occurred within a 10-day window.

*   **Colors (The Communities):**
    *   Each color represents a distinct **"community"** or cluster of politicians who trade in similar patterns. 
    *   If multiple politicians share the same color, it suggests they are part of a group with closely related trading activity.

*   **Size of the Circles (Influence):**
    *   The size of each politician's circle is determined by their **PageRank score**.
    *   A larger circle indicates a more "influential" or "central" politician in the network. This means they are connected to many transactions that are, in turn, connected to other influential politicians.

**In short, the map helps you quickly identify *which politicians are trading together (the colors)* and *who the most important players are within those groups (the sizes)***.

---

### 2. `top_influencers.png`

**What it is:** This is a bar chart that ranks the top 15 politicians based on their influence (PageRank score) in the network.

**How to Read the Chart:**

*   Each bar represents a single politician.
*   The length of the bar shows the politician's **PageRank score**—the higher the score, the more influential they are in the network.
*   The color of the bar corresponds to the **Community ID** they belong to on the main network map, making it easy to see which communities contain the most central players.
