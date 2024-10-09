"""
MAL-Toolbox Attack Graph Attacker Class
"""

from __future__ import annotations
from dataclasses import dataclass, field
import copy
import logging

from typing import Optional
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .attackgraph import AttackGraphNode

logger = logging.getLogger(__name__)

@dataclass
class Attacker:
    name: str
    entry_points: list[AttackGraphNode] = field(default_factory=list)
    reached_attack_steps: list[AttackGraphNode] = \
        field(default_factory=list)
    id: Optional[int] = None

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
        return str(self.to_dict())

    def __deepcopy__(self, memo) -> Attacker:
        """Deep copy an Attacker"""

        # Check if the object is already in the memo dictionary
        if id(self) in memo:
            return memo[id(self)]

        copied_attacker = Attacker(
            id = self.id,
            name = self.name,
        )

        # Remember that self was already copied
        memo[id(self)] = copied_attacker

        copied_attacker.entry_points = copy.deepcopy(
            self.entry_points, memo = memo)
        copied_attacker.reached_attack_steps = copy.deepcopy(
            self.reached_attack_steps, memo = memo)

        return copied_attacker

    def compromise(self, node: AttackGraphNode) -> None:
        """
        Have the attacke compromise the node given as a parameter.

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
