"""Tests for attack graph pattern matching"""
import pytest
from maltoolbox.model import Model, AttackerAttachment
from maltoolbox.attackgraph import AttackGraph
import math
from maltoolbox.patterns.attackgraph_patterns import SearchPattern, SearchCondition

from test_model import create_application_asset, create_association

@pytest.fixture
def example_attackgraph(corelang_spec, model: Model):
    """Fixture that generates an example attack graph
    
    Uses coreLang specification and model with two applications
    with an association and an attacker to create and return
    an AttackGraph object
    """

    # Create 2 assets
    app1 = create_application_asset(model, "Application 1")
    app2 = create_application_asset(model, "Application 2")
    model.add_asset(app1)
    model.add_asset(app2)

    # Create association between app1 and app2
    assoc = create_association(model, from_assets=[app1], to_assets=[app2])
    model.add_association(assoc)

    attacker = AttackerAttachment()
    attacker.entry_points = [
        (app1, ['attemptCredentialsReuse'])
    ]
    model.add_attacker(attacker)

    return AttackGraph(lang_spec=corelang_spec, model=model)


def test_attackgraph_find_pattern(example_attackgraph):
    """Test a simple pattern"""
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda n : n.name == "attemptModify"
            ),
            SearchCondition(
                lambda n : True,
                min_repeated=1, max_repeated=math.inf
            ),
            SearchCondition(
                lambda n : n.name == "attemptRead"
            )
        ]
    )

    paths = pattern.find_matches(example_attackgraph)

    assert paths
    # Make sure the paths match the pattern
    for path in paths:
        conditions = list(pattern.conditions)
        num_matches_curr_condition = 0
        for node in path:
            if conditions[0].matches(node):
                num_matches_curr_condition += 1
            elif not conditions[0].must_match_again(
                num_matches_curr_condition):
                conditions.pop(0)
                num_matches_curr_condition = 0
            else:
                assert False, "Chain does not match pattern conditions"
