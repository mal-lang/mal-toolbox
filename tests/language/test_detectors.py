
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

    assert app1_exploit.detectors["logExploit"].context, "Expected context for 'logExploit' detector"
    assert "comp" in app1_exploit.detectors["logExploit"].context, "Expected 'comp' in the context of 'logExploit' detector"
    context_item = app1_exploit.detectors["logExploit"].context["comp"]
    assert context_item.label == "comp", "Expected context label to be 'comp'"
    assert context_item.asset_type.name == "Computer", "Expected context asset type to be 'Computer'"
    assert context_item.attack_step_name == "authenticate", "Expected context attack step name to be 'authenticate'"
    assert context_item.expr is not None, "Expected an expression chain in the context item of 'logExploit' detector"