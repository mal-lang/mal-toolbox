from __future__ import annotations
import logging
import zipfile
from maltoolbox.exceptions import AttackGraphStepExpressionError
from maltoolbox.language.languagegraph import LanguageGraph
from maltoolbox.model import Model

from maltoolbox.attackgraph.attackgraph import AttackGraph

from .. import log_configs
logger = logging.getLogger(__name__)


def create_attack_graph(
        lang: str | LanguageGraph,
        model: str | Model,
    ) -> AttackGraph:
    """Create and return an attack graph

    Args:
    ----
    lang    - path to language file (.mar or .mal) or a LanguageGraph object
    model   - path to model file (yaml or json) or a Model object

    """
    # Load language
    if isinstance(lang, LanguageGraph):
        lang_graph = lang
    elif isinstance(lang, str):
        # Load from path
        try:
            lang_graph = LanguageGraph.from_mar_archive(lang)
        except zipfile.BadZipFile:
            lang_graph = LanguageGraph.from_mal_spec(lang)
    else:
        raise TypeError("`lang` must be either string or LanguageGraph")

    if 'langspec_file' in log_configs:
        lang_graph.save_language_specification_to_json(
            log_configs['langspec_file']
        )

    if 'langgraph_file' in log_configs:
        lang_graph.save_to_file(log_configs['langgraph_file'])

    # Load model
    if isinstance(model, Model):
        instance_model = model
    elif isinstance(model, str):
        # Load from path
        instance_model = Model.load_from_file(model, lang_graph)
    else:
        raise TypeError("`model` must be either string or Model")

    if log_configs['model_file']:
        instance_model.save_to_file(log_configs['model_file'])

    try:
        attack_graph = AttackGraph(lang_graph, instance_model)

    except AttackGraphStepExpressionError as e:
        logger.error(
            'Attack graph generation failed when attempting '
            'to resolve attack step expression!'
        )
        raise e

    return attack_graph
