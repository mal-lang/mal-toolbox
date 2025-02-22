"""
MAL-Toolbox Attack Graph Attacker Class
"""

from __future__ import annotations
import logging

from typing import Optional
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .attackgraph import AttackGraphNode

logger = logging.getLogger(__name__)

class Attacker:

    def __init__(
        self,
        name: str,
        entry_points: Optional[set[AttackGraphNode]] = None,
        reached_attack_steps: Optional[set[AttackGraphNode]] = None,
        attacker_id: Optional[int] = None
    ):
        self.name = name
        self.id = attacker_id
        self.entry_points = entry_points or set()
        self.reached_attack_steps: set[AttackGraphNode] = set()
        for node in reached_attack_steps or {}:
            self.compromise(node)

    def to_dict(self) -> dict:
        attacker_dict: dict = {
            'id': self.id,
            'name': self.name,
            'entry_points': {},
            'reached_attack_steps': {}
        }

        for entry_point in self.entry_points:
            attacker_dict['entry_points'][entry_point.id] = \
                entry_point.full_name
        for attack_step in self.reached_attack_steps:
            attacker_dict['reached_attack_steps'][attack_step.id] = \
                attack_step.full_name

        return attacker_dict

    def __repr__(self) -> str:
        return f'Attacker(name: "{self.name}", id: {self.id})'

    def compromise(self, node: AttackGraphNode) -> None:
        """
        Have the attacker compromise the node given as a parameter.

        Arguments:
        node    - the node that the attacker will compromise
        """

        logger.debug(
            'Attacker "%s"(%d) is compromising node "%s"(%d).',
            self.name,
            self.id,
            node.full_name,
            node.id
        )
        if node.is_compromised_by(self):
            logger.info(
                'Attacker "%s"(%d) already compromised node "%s"(%d). '
                'Do nothing.',
                self.name,
                self.id,
                node.full_name,
                node.id
            )
            return

        node.compromised_by.add(self)
        self.reached_attack_steps.add(node)

    def undo_compromise(self, node: AttackGraphNode) -> None:
        """
        Remove the attacker from the list of attackers that have compromised
        the node given as a parameter.

        Arguments:
        node    - the node that we wish to remove this attacker from.
        """

        logger.debug(
            'Removing attacker "%s"(%d) from compromised_by '
            'list of node "%s"(%d).',
            self.name,
            self.id,
            node.full_name,
            node.id
        )
        if not node.is_compromised_by(self):
            logger.info(
                'Attacker "%s"(%d) had not compromised node "%s"(%d).'
                ' Do nothing.',
                self.name,
                self.id,
                node.full_name,
                node.id
            )
            return

        node.compromised_by.remove(self)
        self.reached_attack_steps.remove(node)
