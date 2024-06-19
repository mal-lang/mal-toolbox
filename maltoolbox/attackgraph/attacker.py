"""
MAL-Toolbox Attack Graph Attacker Class
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .attackgraph import AttackGraphNode

logger = logging.getLogger(__name__)

@dataclass
class Attacker:
    name: str
    entry_points: list[node.AttackGraphNode] = field(default_factory=list)
    reached_attack_steps: list[node.AttackGraphNode] = \
        field(default_factory=list)
    id: int = None

    def to_dict(self) -> dict:
        attacker_dict = {
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
        return str(self.to_dict())

    def compromise(self, node: AttackGraphNode) -> None:
        """
        Have the attacke compromise the node given as a parameter.

        Arguments:
        node    - the node that the attacker will compromise
        """

        logger.debug(
            'Attacker "%s(%d)" is compromising node "%s".',
            self.name,
            self.id,
            node.full_name
        )
        if node.is_compromised_by(self):
            logger.info(
                'Attacker "%s(%d)" already compromised node "%s". '
                'Do nothing.',
                self.name,
                self.id,
                node.full_name
            )
            return

        node.compromised_by.append(self)
        self.reached_attack_steps.append(node)

    def undo_compromise(self, node: AttackGraphNode) -> None:
        """
        Remove the attacker from the list of attackers that have compromised
        the node given as a parameter.

        Arguments:
        node    - the node that we wish to remove this attacker from.
        """

        logger.debug(
            'Removing attacker "%s(%d)" from compromised_by '
            'list of node "%s".',
            self.name,
            self.id,
            node.full_name
        )
        if not node.is_compromised_by(self):
            logger.info(
                'Attacker "%s(%d)" had not compromised node "%s". Do nothing.',
                self.name,
                self.id,
                node.full_name
            )
            return

        node.compromised_by.remove(self)
        self.reached_attack_steps.remove(node)
