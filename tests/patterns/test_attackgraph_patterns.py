"""Tests for attack graph pattern matching"""
import pytest
from maltoolbox.model import Model, AttackerAttachment
from maltoolbox.attackgraph import AttackGraph

import maltoolbox.patterns.attackgraph_patterns as attackgraph_patterns
from maltoolbox.patterns.attackgraph_patterns import AttackGraphPattern

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
    patterns = [
        AttackGraphPattern(
            attributes=[('name', 'attemptRead')],
            min_repeated=1, max_repeated=1
        ),
        AttackGraphPattern(
            attributes=[('name', 'successfulRead')],
            min_repeated=1, max_repeated=1
        ),
        AttackGraphPattern(
            attributes=[('name', 'read')],
            min_repeated=1, max_repeated=1
        ),
    ]
    chains = attackgraph_patterns.find_in_graph(example_attackgraph, patterns)
    breakpoint()