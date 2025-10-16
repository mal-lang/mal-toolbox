from __future__ import annotations
from typing import Iterable

import networkx as nx
from maltoolbox.attackgraph import AttackGraph, AttackGraphNode
from maltoolbox.model import Model


def attack_graph_to_digraph(nodes: AttackGraph | Iterable[AttackGraphNode]) -> nx.DiGraph:
    if isinstance(nodes, AttackGraph):
        nodes = list(nodes.nodes.values())
    G = nx.DiGraph()

    for node in nodes:
        G.add_node(node.id, **node.to_dict())
        G.nodes[node.id]["full_name"] = node.full_name

    edges = [(node.id, child.id) for node in nodes for child in node.children]
    edges += [(parent.id, node.id) for node in nodes for parent in node.parents]
    G.add_edges_from(edges)

    return G


def model_to_graph(model: Model) -> nx.Graph:
    G = nx.Graph()

    for id, asset in model.assets.items():
        asset_dict = asset._to_dict()[id]
        asset_dict["id"] = id
        G.add_node(id, **asset_dict)

    for id, asset in model.assets.items():
        for fieldname, associated_assets in asset.associated_assets.items():
            for associated_asset in associated_assets:
                G.add_edge(id, associated_asset.id, **{"name": asset.lg_asset.associations[fieldname].name})

    return G