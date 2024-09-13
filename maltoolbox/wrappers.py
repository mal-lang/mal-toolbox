"""Contains wrappers combining more than one of the maltoolbox submodules"""

import logging
import sys
import zipfile

from maltoolbox.model import Model
from maltoolbox.language import LanguageGraph, LanguageClassesFactory
from maltoolbox.attackgraph import AttackGraph
from maltoolbox.attackgraph.analyzers.apriori import (
    calculate_viability_and_necessity
)
from maltoolbox.exceptions import AttackGraphStepExpressionError
from maltoolbox import log_configs


logger = logging.getLogger(__name__)

def create_attack_graph(
        lang_file: str,
        model_file: str,
        attach_attackers=True,
        calc_viability_and_necessity=True
    ) -> AttackGraph:
    """Create and return an attack graph

    Args:
    lang_file                       - path to language file (.mar or .mal)
    model_file                      - path to model file (yaml or json)
    attach_attackers                - whether to run attach_attackers or not
    calc_viability_and_necessity    - whether run apriori calculations or not
    """
    try:
        lang_graph = LanguageGraph.from_mar_archive(lang_file)
    except zipfile.BadZipFile:
        lang_graph = LanguageGraph.from_mal_spec(lang_file)

    if log_configs['langspec_file']:
        lang_graph.save_to_file(log_configs['langspec_file'])

    lang_classes_factory = LanguageClassesFactory(lang_graph)
    instance_model = Model.load_from_file(model_file, lang_classes_factory)

    if log_configs['model_file']:
        instance_model.save_to_file(log_configs['model_file'])

    try:
        attack_graph = AttackGraph(lang_graph, instance_model)
    except AttackGraphStepExpressionError:
        logger.error(
            'Attack graph generation failed when attempting '
            'to resolve attack step expression!'
        )
        sys.exit(1)

    if attach_attackers:
        attack_graph.attach_attackers()

    if calc_viability_and_necessity:
        calculate_viability_and_necessity(attack_graph)

    return attack_graph
