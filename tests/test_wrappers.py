from conftest import path_testdata

from maltoolbox.wrappers import create_attack_graph


def test_create_attack_graph() -> None:
    """See that the create attack graph wrapper works."""
    mar = path_testdata('org.mal-lang.coreLang-1.0.0.mar')
    model = path_testdata('simple_example_model.yml')

    # Make sure that it runs without errors
    create_attack_graph(mar, model)
