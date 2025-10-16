"""Tests for networkx conversion"""

from maltoolbox.attackgraph import AttackGraph
from maltoolbox.translators import attack_graph_to_nx, model_to_nx
from maltoolbox.model import Model
import networkx as nx

def test_attackgraph_to_nx(example_attackgraph: AttackGraph):
    """Test conversion of attack graph to networkx digraph"""

    def number_of_edges(attack_graph: AttackGraph) -> int:
        edges = set()
        for node in attack_graph.nodes.values():
            for child in node.children:
                edges.add((node.id, child.id))
            for parent in node.parents:
                edges.add((parent.id, node.id))
        return len(edges)

    no_edges = number_of_edges(example_attackgraph)
    G = attack_graph_to_nx(example_attackgraph)

    assert isinstance(G, nx.DiGraph)
    assert len(G.nodes) == len(example_attackgraph.nodes)
    assert number_of_edges(example_attackgraph) == no_edges

    for node in example_attackgraph.nodes.values():
        nx_node_attrs = G.nodes[node.id]
        assert nx_node_attrs['id'] == node.id
        assert nx_node_attrs['type'] == node.type
        assert nx_node_attrs['lang_graph_attack_step'] == node.lg_attack_step.full_name
        assert nx_node_attrs['name'] == node.name
        assert nx_node_attrs['ttc'] == node.ttc
        assert nx_node_attrs['children'] == {child.id: child.full_name for child in node.children}
        assert nx_node_attrs['parents'] == {parent.id: parent.full_name for parent in node.parents}

        for child in node.children:
            assert G.has_edge(node.id, child.id)
        for parent in node.parents:
            assert G.has_edge(parent.id, node.id)

def test_model_to_nx(example_model: Model):
    """Test conversion of model to networkx digraph"""

    def number_of_edges(model: Model) -> int:
        edges = set()
        for asset in model.assets.values():
            for _fieldname, associated_assets in asset.associated_assets.items():
                for associated_asset in associated_assets:
                    edges.add((asset.id, associated_asset.id))
        return len(edges)

    no_edges = number_of_edges(example_model)
    G = model_to_nx(example_model)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == len(example_model.assets)
    assert number_of_edges(example_model) == no_edges
    for asset in example_model.assets.values():
        nx_node_attrs = G.nodes[asset.id]
        assert nx_node_attrs['id'] == asset.id
        assert nx_node_attrs['type'] == asset.type
        assert nx_node_attrs['name'] == asset.name
        assert nx_node_attrs['associated_assets'] == {fieldname: {associated_asset.id: associated_asset.name for associated_asset in associated_assets} for fieldname, associated_assets in asset.associated_assets.items()}

        for associated_asset in asset.associated_assets.values():
            for fieldname, associated_assets in asset.associated_assets.items():
                for associated_asset in associated_assets:
                    assert G.has_edge(asset.id, associated_asset.id)
                    assert G.get_edge_data(asset.id, associated_asset.id)['name'] == asset.lg_asset.associations[fieldname].name

