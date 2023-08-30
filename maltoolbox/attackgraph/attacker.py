"""
MAL-Toolbox Attack Graph Attacker Class
"""

from dataclasses import dataclass
from typing import List, ForwardRef

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
