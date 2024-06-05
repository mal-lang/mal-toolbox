from maltoolbox.wrappers import create_attack_graph
from conftest import path_testdata

def test_create_attack_graph():
    """See that the create attack graph wrapper works"""
    mar = path_testdata('org.mal-lang.coreLang-1.0.0.mar')
    model = path_testdata('simple_example_model.json')

    # Make sure that it runs without errors
    create_attack_graph(mar, model)
