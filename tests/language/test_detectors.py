
from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.model import Model
from maltoolbox.language.languagegraph import LanguageGraph
from conftest import path_testdata
import pytest

@pytest.fixture
def detectorlang_lang_graph():
    """Fixture that returns the detectorLang language specification as dict"""
    mal_file_path = path_testdata("detector_lang.mal")
    return LanguageGraph.from_mal_spec(mal_file_path)

@pytest.fixture
def example_detectorlang_model(detectorlang_lang_graph: LanguageGraph):
    """Fixture that generates an example model

    Uses detectorLang specification to create and return a Model object
    with two applications with an association
    """
    model = Model(name='Example Model', lang_graph=detectorlang_lang_graph)
    app1 = model.add_asset(asset_type='Application', name='Application 1')
    app2 = model.add_asset(asset_type='Application', name='Application 2')
    app1.add_associated_assets(fieldname='toApplications', assets={app2})
    return model

@pytest.fixture
def detectorlang_attack_graph(example_detectorlang_model: Model):
    """Fixture that generates an attack graph from the example detectorLang model"""
    return AttackGraph(example_detectorlang_model.lang_graph, example_detectorlang_model)

def test_detector_presence(detectorlang_attack_graph: AttackGraph):
    """Test that the detector is present in the model as expected"""

    app1_exploit = detectorlang_attack_graph.get_node_by_full_name("Application 1:exploit")
    assert app1_exploit.detectors, "Expected detectors on the 'exploit' attack step of Application 1"
    detector_names = [det.name for det in app1_exploit.detectors.values()]
    assert "logExploit" in detector_names, "Expected 'logExploit' detector on the 'exploit' attack step of Application 1"
    context_item_computer = app1_exploit.detectors['logExploit'].context['computer']
    assert context_item_computer.asset.name == "Computer", "Expected 'computer' context item to refer to asset of type 'Computer'"
    assert context_item_computer.attack_step == "authenticate", "Expected 'computer' context item to refer to 'authenticate' attack step"
    assert context_item_computer.expression_chain is not None, "Expected 'computer' context item to have an expression chain"
    assert context_item_computer.expression_chain.type == "field", "Expected 'computer' context item to have expression chain of type 'field'"
    assert context_item_computer.expression_chain.fieldname == "computerOfApp", "Expected 'computer' context item to have expression chain with fieldname 'computerOfApp'"