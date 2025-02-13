"""
MAL-Toolbox Attack Graph Attacker Class
"""

from __future__ import annotations
import copy
import logging

from typing import Optional
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .attackgraph import AttackGraphNode

logger = logging.getLogger(__name__)

class Attacker:

    _max_id = -1

    def __init__(
        self,
        name: str,
        entry_points: set[AttackGraphNode] = None,
        reached_attack_steps: set[AttackGraphNode] = None,
        attacker_id: Optional[int] = None,
    ):
        self.name = name
        self.entry_points = entry_points or set()
        self.reached_attack_steps = reached_attack_steps or set()

        Attacker._max_id = max(Attacker._max_id + 1, attacker_id or 0)
        self.id = Attacker._max_id

    @staticmethod
    def reset_ids(id=None):
        Attacker._max_id = id if id is not None else -1

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
        return 'Attacker(name: "%s", id: %d)' % (
            self.name, self.id if self.id is not None else -1)

    def __deepcopy__(self, memo) -> Attacker:
        """Deep copy an Attacker"""

        # Check if the object is already in the memo dictionary
        if id(self) in memo:
            return memo[id(self)]

        old_max_id = Attacker._max_id
        Attacker.reset_ids()
        copied_attacker = Attacker(
            name = self.name,
            attacker_id = self.id,
            entry_points = set(),
            reached_attack_steps = set()
        )
        Attacker.reset_ids(old_max_id)

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
