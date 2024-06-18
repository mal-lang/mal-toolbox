from __future__ import annotations

"""
MAL-Toolbox Attack Graph Attacker Class
"""

import logging

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Attacker:
    name: str
    entry_points: list[node.AttackGraphNode] = field(default_factory=list)
    reached_attack_steps: list[node.AttackGraphNode] = \
        field(default_factory=list)
    id: int = None

    def to_dict(self):
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

    def __repr__(self):
        return str(self.to_dict())

    def compromise(self, node):
        """
        Have the attacke compromise the node given as a parameter.

        Arguments:
        node    - the node that the attacker will compromise
        """

        logger.debug(f'Attacker \"{self.id}\" is compromising node '
            f'\"{node.id}\".')
        if node.is_compromised_by(self):
            logger.info(f'Attacker \"{self.id}\" had already compromised '
                f'node \"{node.id}\". Do nothing.')
            return

        node.compromised_by.append(self)
        self.reached_attack_steps.append(node)

    def undo_compromise(self, node):
        """
        Remove the attacker from the list of attackers that have compromised
        the node given as a parameter.

        Arguments:
        node    - the node that we wish to remove this attacker from.
        """

        logger.debug(f'Attacker \"{self.id}\" is being removed from the '
            f'compromised_by list of node \"{node.id}\".')
        if not node.is_compromised_by(self):
            logger.info(f'Attacker \"{self.id}\" had not compromised '
                f'node \"{node.id}\". Do nothing.')
            return

        node.compromised_by.remove(self)
        self.reached_attack_steps.remove(node)
