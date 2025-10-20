
from __future__ import annotations

import networkx as nx

from maltoolbox.attackgraph import AttackGraph
from .networkx import attack_graph_to_nx


def attack_graph_to_gexf(attack_graph: AttackGraph, output_path: str) -> None:
    """Export an attack graph to Gephi-compatible GEXF format

    Arguments:
    attack_graph   - the attack graph to export
    output_path    - file path where the .gexf file will be written
    """
    G: nx.DiGraph = attack_graph_to_nx(attack_graph)
    nx.write_gexf(G, output_path)
