"""
MAL-Toolbox Attack Graph Attacker Class
"""

import logging

from dataclasses import dataclass
from typing import List, ForwardRef

logger = logging.getLogger(__name__)

@dataclass
class Attacker:
    id: str
    entry_points: List[ForwardRef("node.AttackGraphNode")]
    reached_attack_steps: List[ForwardRef("node.AttackGraphNode")]
    node: ForwardRef("node.AttackGraphNode")

    def to_dict(self):
        attacker_dict = {
            "id": self.id,
            "entry_points": [entry_point.id for entry_point in
                self.entry_points],
            "reached_attack_steps": [attack_step.id for attack_step in
                self.reached_attack_steps],
            "node": self.node.id
        }

        return attacker_dict

    def compromise(self, node):
        """
        Have the attacke compromise the node given as a parameter.

        Arguments:
        node    - the node that the attacker will compromise
        """

        logger.debug(f'Attacker \"{self.id}\" is compromising node '
            f'\"{node.id}\".')
        if self in node.compromised_by:
            logger.info(f'Attacker \"{self.id}\" had already compromised '
                f'node \"{node.id}\". Do nothing.')
            return

        node.compromised_by.append(self)
        self.reached_attack_steps.append(node)
