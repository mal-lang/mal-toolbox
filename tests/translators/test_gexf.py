from maltoolbox.model import Model
from maltoolbox.translators import attack_graph_to_gexf, model_to_gexf
from maltoolbox.attackgraph import AttackGraph
import pytest
from gexfpy import stringify
import xml.etree.ElementTree as ET

def test_attack_graph_to_gexf(example_attackgraph: AttackGraph):
    """Test conversion of attack graph to GEXF format"""

    def number_of_edges(attack_graph: AttackGraph) -> int:
        edges = set()
        for node in attack_graph.nodes.values():
            for child in node.children:
                edges.add((node.id, child.id))
            for parent in node.parents:
                edges.add((parent.id, node.id))
        return len(edges)


    gexf = attack_graph_to_gexf(example_attackgraph)

    assert gexf.graph.nodes.count == len(example_attackgraph.nodes)
    assert gexf.graph.edges.count == number_of_edges(example_attackgraph)

    for node in example_attackgraph.nodes.values():
        assert gexf.graph.nodes.node[node.id].id == node.id, f"Node id mismatch"
        assert gexf.graph.nodes.node[node.id].label == node.full_name, f"Node label mismatch"
        node_dict = node.to_dict()
        for attvalue in gexf.graph.nodes.node[node.id].attvalues.attvalue:
            assert str(node_dict[attvalue.for_value]) == attvalue.value, f"Attribute {attvalue.for_value} value mismatch"

    try:
        ET.fromstring(stringify(gexf))
    except ET.ParseError as e:
        pytest.fail(f"Output is not valid XML: {e}")

def test_model_to_gexf(example_model: Model):
    """Test conversion of model to GEXF format"""

    def number_of_edges(model: Model) -> int:
        edges = set()
        for asset in model.assets.values():
            for _fieldname, associated_assets in asset.associated_assets.items():
                for associated_asset in associated_assets:
                    edges.add((asset.id, associated_asset.id))
        return len(edges)

    gexf = model_to_gexf(example_model)

    assert gexf.graph.nodes.count == len(example_model.assets)
    assert gexf.graph.edges.count == number_of_edges(example_model)

    for asset in example_model.assets.values():
        assert gexf.graph.nodes.node[asset.id].id == asset.id, f"Node id mismatch"
        assert gexf.graph.nodes.node[asset.id].label == asset.name, f"Node label mismatch"
        asset_dict = asset._to_dict()[asset.id]
        for attvalue in gexf.graph.nodes.node[asset.id].attvalues.attvalue:
            assert str(asset_dict[attvalue.for_value]) == attvalue.value, f"Attribute {attvalue.for_value} value mismatch"

    try:
        ET.fromstring(stringify(gexf))
    except ET.ParseError as e:
        pytest.fail(f"Output is not valid XML: {e}")