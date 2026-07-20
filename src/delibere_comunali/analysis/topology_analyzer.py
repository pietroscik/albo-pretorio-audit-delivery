"""
Module for analyzing the topology of a knowledge graph.

This refactors the logic from the legacy `scripts/analyze_topology.py`
into a modern, importable module.
"""

import networkx as nx
from pathlib import Path


def analyze_graph_topology(graph: nx.Graph) -> dict:
    """Calculates and returns key topology metrics for a given graph."""
    if not isinstance(graph, (nx.Graph, nx.DiGraph)):
        raise TypeError("Input must be a NetworkX Graph object.")

    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    if num_nodes == 0:
        return {
            "nodes": 0,
            "edges": 0,
            "density": 0,
            "avg_degree": 0,
            "components": 0,
        }

    density = nx.density(graph)

    degrees = [val for (node, val) in graph.degree()]
    avg_degree = sum(degrees) / num_nodes if num_nodes > 0 else 0

    # Use the appropriate component calculation for directed or undirected graphs
    if graph.is_directed():
        components = nx.number_weakly_connected_components(graph)
    else:
        components = nx.number_connected_components(graph)

    return {
        "nodes": num_nodes,
        "edges": num_edges,
        "density": round(density, 4),
        "avg_degree": round(avg_degree, 2),
        "components": components,
    }


def main(ente: str, base_dir: str):
    """Main function to load a graph and print its topology analysis."""
    if not ente:
        raise ValueError("Argument 'ente' is required.")

    base_path = Path(base_dir)
    report_dir = base_path / "report"
    gexf_path = report_dir / "knowledge_graph.gexf"

    if not gexf_path.exists():
        raise FileNotFoundError(f"File del grafo non trovato in {gexf_path}. Esegui prima 'build-kg'.")

    G = nx.read_gexf(gexf_path)
    metrics = analyze_graph_topology(G)

    print("\n--- Risultati Analisi Topologica ---")
    for key, value in metrics.items():
        print(f"  - {key.replace('_', ' ').capitalize()}: {value}")
    print("------------------------------------")