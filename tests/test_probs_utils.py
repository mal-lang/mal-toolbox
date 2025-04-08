"""Unit tests for the probabilities utilities module"""

import pytest

from maltoolbox.model import Model
from maltoolbox.attackgraph.attackgraph import AttackGraph
from maltoolbox.probs_utils import calculate_prob, ProbCalculationMethod

def test_probs_utils(model: Model):
    """Test TTC calculation for nodes"""

    app = model.add_asset('Application')
    creds = model.add_asset('Credentials')
    user = model.add_asset('User')
    identity = model.add_asset('Identity')
    vuln = model.add_asset('SoftwareVulnerability')

    identity.add_associated_assets('credentials', {creds})
    user.add_associated_assets('userIds', {identity})
    app.add_associated_assets('highPrivAppIAMs', {identity})
    app.add_associated_assets('vulnerabilities', {vuln})

    attack_graph = AttackGraph(model.lang_graph, model)

    for node in attack_graph.nodes.values():
        #TODO: Actually check some of the results
        calculate_prob(node.ttc, ProbCalculationMethod.SAMPLE)

    for node in attack_graph.nodes.values():
        #TODO: Actually check some of the results
        calculate_prob(node.ttc, ProbCalculationMethod.EXPECTED)
