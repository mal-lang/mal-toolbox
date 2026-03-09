
from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.attackgraph.detector import Detector
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
    comp1 = model.add_asset(asset_type='Computer', name='Computer 1')
    app1 = model.add_asset(asset_type='Application', name='Application 1')
    app2 = model.add_asset(asset_type='Application', name='Application 2')
    comp1.add_associated_assets(fieldname='computerApps', assets={app1})
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

    log_exploit_detector: Detector = app1_exploit.detectors["logExploit"]
    assert log_exploit_detector.tprate == 0.9, "Expected a TPRate for 'logExploit' detector"
    assert log_exploit_detector.fprate == 0.1, "Expected an FPRate for 'logExploit' detector"
    assert log_exploit_detector.potential_context, "Expected context for 'logExploit' detector"
    assert "comp" in log_exploit_detector.potential_context, "Expected 'comp' in the context of 'logExploit' detector"
    potential_comp_nodes = log_exploit_detector.potential_context["comp"]
    assert len(potential_comp_nodes) == 1, "Expected exactly one potential node for 'comp' in the context of 'logExploit' detector"
    comp_node = next(iter(potential_comp_nodes))
    assert comp_node.full_name == "Computer 1:authenticate", "Expected the potential 'comp' node to be associated with 'Computer 1'"


def test_detector_unlabeled_context():
    """Test that a detector with an unlabeled context field is handled correctly"""

    lang_str = """
    #id: "test-actions-effects"
    #version: "0.0.0"

    category System{
        asset Computer {
        & physicalAccess
            -> attemptAuthenticate

        | attemptAuthenticate [HardAndCertain]
            -> authenticate

        & effect authenticate
            -> computerApps.attemptExploit
        }

        asset Application {
        # shutDown
            -> exploit

        | attemptExploit [HardAndCertain]
            -> exploit

        & effect exploit
            ! logExploit (computerOfApp.authenticate) [tpr: 0.9, fpr: 0.1]
            -> toApplications.attemptExploit,
            dataOnApp.read
        }

        asset Data {
        | read
        }
    }

    associations {
        Computer [computerOfApp] * <-- appExecution --> * [computerApps] Application
        Application [fromApplications] * <-- AppToAppCommunication --> * [toApplications] Application
        Data [dataOnApp] * <-- AppData --> * [appWithData] Application
    }

    """
    tmp_lang_file = "/tmp/temp_detector_lang.mal"
    with open(tmp_lang_file, "w") as f:
        f.write(lang_str)

    lang_graph = LanguageGraph.from_mal_spec(tmp_lang_file)
    model = Model(name='Test Model', lang_graph=lang_graph)
    comp1 = model.add_asset(asset_type='Computer', name='Computer 1')
    app1 = model.add_asset(asset_type='Application', name='Application 1')
    comp1.add_associated_assets(fieldname='computerApps', assets={app1})

    attack_graph = AttackGraph(lang_graph, model)
    app1_exploit = attack_graph.get_node_by_full_name("Application 1:exploit")
    detectors = app1_exploit.detectors
    assert detectors, "Expected detectors on the 'exploit' attack step of Application 1"
    context = detectors["logExploit"].potential_context
    assert context == {
        'computerOfApp.authenticate': {
            attack_graph.get_node_by_full_name("Computer 1:authenticate")
        }
    }