"""MAL-Toolbox Attack Graph Module
"""
from __future__ import annotations
import logging
from ..str_utils import levenshtein_distance
from .node import AttackGraphNode


logger = logging.getLogger(__name__)

def get_similar_full_names(
    full_name_to_node: dict[str, AttackGraphNode], q: str
):
    shortest_dist = 100
    similar_names = []

    for full_name in full_name_to_node:
        dist = levenshtein_distance(q, full_name)
        if dist == shortest_dist:
            similar_names.append(full_name)
        elif dist < shortest_dist:
            similar_names = [full_name]
            shortest_dist = dist

    return similar_names


def get_node_by_full_name(full_name_to_node: dict[str, AttackGraphNode], full_name: str):
    logger.debug('Looking up node with full name "%s"', full_name)
    if full_name not in full_name_to_node:
        similar_names = get_similar_full_names(full_name_to_node, full_name)
        raise LookupError(
            f'Could not find node with name "{full_name}". '
            f'Did you mean: {", ".join(similar_names)}?'
        )
    return full_name_to_node[full_name]
