"""
MAL-Toolbox Attack Graph Node
"""

from __future__ import annotations
import copy
from functools import cached_property
from typing import TYPE_CHECKING
import numpy as np
import math

if TYPE_CHECKING:
    from typing import Any, Optional
    from . import Attacker
    from ..language import LanguageGraphAttackStep
    from ..model import ModelAsset

class AttackGraphNode:
    """Node part of AttackGraph"""

    def __init__(
        self,
        node_id: int,
        lg_attack_step: LanguageGraphAttackStep,
        model_asset: Optional[ModelAsset] = None,
        defense_status: Optional[float] = None,
        existence_status: Optional[bool] = None
    ):
        self.lg_attack_step = lg_attack_step
        self.name = lg_attack_step.name
        self.type = lg_attack_step.type
        self.ttc = lg_attack_step.ttc
        self.tags = lg_attack_step.tags
        self.detectors = lg_attack_step.detectors

        self.id = node_id
        self.model_asset = model_asset
        self.defense_status = defense_status
        self.existence_status = existence_status

        self.children: set[AttackGraphNode] = set()
        self.parents: set[AttackGraphNode] = set()
        self.is_viable: bool = True
        self.is_necessary: bool = True
        self.compromised_by: set[Attacker] = set()
        self.extras: dict = {}

    def to_dict(self) -> dict:
        """Convert node to dictionary"""
        node_dict: dict = {
            'id': self.id,
            'type': self.type,
            'lang_graph_attack_step': self.lg_attack_step.full_name,
            'name': self.name,
            'ttc': self.ttc,
            'children': {child.id: child.full_name for child in
                self.children},
            'parents': {parent.id: parent.full_name for parent in
                self.parents},
            'compromised_by': [attacker.name for attacker in \
                self.compromised_by]
        }

        for detector in self.detectors.values():
            node_dict.setdefault('detectors', {})[detector.name] = detector.to_dict()
        if self.model_asset is not None:
            node_dict['asset'] = str(self.model_asset.name)
        if self.defense_status is not None:
            node_dict['defense_status'] = str(self.defense_status)
        if self.existence_status is not None:
            node_dict['existence_status'] = str(self.existence_status)
        if self.is_viable is not None:
            node_dict['is_viable'] = str(self.is_viable)
        if self.is_necessary is not None:
            node_dict['is_necessary'] = str(self.is_necessary)
        if self.tags:
            node_dict['tags'] = list(self.tags)
        if self.extras:
            node_dict['extras'] = self.extras

        return node_dict


    def __repr__(self) -> str:
        return (f'AttackGraphNode(name: "{self.full_name}", id: {self.id}, '
            f'type: {self.type})')


    def __deepcopy__(self, memo) -> AttackGraphNode:
        """Deep copy an attackgraph node

        The deepcopy will copy over node specific information, such as type,
        name, etc., but it will not copy attack graph relations such as
        parents, children, or attackers it is compromised by. These references
        should be recreated when deepcopying the attack graph itself.

        """

        # Check if the object is already in the memo dictionary
        if id(self) in memo:
            return memo[id(self)]

        copied_node = AttackGraphNode(
            node_id = self.id,
            model_asset = self.model_asset,
            lg_attack_step = self.lg_attack_step
        )

        copied_node.tags = copy.deepcopy(self.tags, memo)
        copied_node.extras = copy.deepcopy(self.extras, memo)
        copied_node.ttc = copy.deepcopy(self.ttc, memo)

        copied_node.defense_status = self.defense_status
        copied_node.existence_status = self.existence_status
        copied_node.is_viable = self.is_viable
        copied_node.is_necessary = self.is_necessary

        # Remember that self was already copied
        memo[id(self)] = copied_node

        return copied_node


    def is_compromised(self) -> bool:
        """
        Return True if any attackers have compromised this node.
        False, otherwise.
        """
        return len(self.compromised_by) > 0


    def is_compromised_by(self, attacker: Attacker) -> bool:
        """
        Return True if the attacker given as an argument has compromised this
        node.
        False, otherwise.

        Arguments:
        attacker    - the attacker we are interested in
        """
        return attacker in self.compromised_by


    def compromise(self, attacker: Attacker) -> None:
        """
        Have the attacker given as a parameter compromise this node.

        Arguments:
        attacker    - the attacker that will compromise the node
        """
        attacker.compromise(self)


    def undo_compromise(self, attacker: Attacker) -> None:
        """
        Remove the attacker given as a parameter from the list of attackers
        that have compromised this node.

        Arguments:
        attacker    - the attacker that we wish to remove from the compromised
                      list.
        """
        attacker.undo_compromise(self)


    def is_enabled_defense(self) -> bool:
        """
        Return True if this node is a defense node and it is enabled and not
        suppressed via tags.
        False, otherwise.
        """
        return self.type == 'defense' and \
            'suppress' not in self.tags and \
            self.defense_status == 1.0


    def is_available_defense(self) -> bool:
        """
        Return True if this node is a defense node and it is not fully enabled
        and not suppressed via tags. False otherwise.
        """
        return self.type == 'defense' and \
            'suppress' not in self.tags and \
            self.defense_status != 1.0

    def ttc_sample(self) -> float:
        """Sample a value from ttc distribution for a node

        TTC Distributions in MAL:
        https://mal-lang.org/mal-langspec/apidocs/org.mal_lang.langspec/org/mal_lang/langspec/ttc/TtcDistribution.html
        """

        def sample(exponential: float, bernoulli=1.0):
            """
            Generate a random sample for the given distributions.
            If bernoulli distribution is not given, the sample will
            simply be from an exponential.

            If the Bernoulli trial fails (0), return infinity (impossible).
            If the Bernoulli trial succeeds (1), return sample from
            exponential distribution.
            """

            # If bernoulli is set to 1, the sample is just exponential
            if np.random.choice([0, 1], p=[1 - bernoulli, bernoulli]):
                return np.random.exponential(scale=1 / exponential)
            return math.inf

        if self.type == "defense":
            # Defenses have no ttc
            return 0

        distribution = self.ttc.get('name')
        s = math.nan
        if distribution == "EasyAndCertain":
            s = sample(exponential=1)
        elif distribution == "EasyAndUncertain":
            s = sample(exponential=1, bernoulli=0.5)
        elif distribution == "HardAndCertain":
            s = sample(exponential=0.1)
        elif distribution == "HardAndUncertain":
            s = sample(exponential=0.1, bernoulli=0.5)
        elif distribution == "VeryHardAndCertain":
            s = sample(exponential=0.01)
        elif distribution == "VeryHardAndUncertain":
            s = sample(exponential=0.01, bernoulli=0.5)
        elif distribution == "Exponential":
            scale = float(self.ttc['arguments'][0])
            s = sample(exponential=scale)
        else:
            raise ValueError(f"Unknown TTC distribution: {distribution}")

        return s

    def ttc_expected_value(self) -> float:
        """Returns the expected value of the ttc distribution for a node.

        TTC Distributions in MAL:
        https://mal-lang.org/mal-langspec/apidocs/org.mal_lang.langspec/org/mal_lang/langspec/ttc/TtcDistribution.html
        """

        def expected_value(exponential: float, bernoulli=1.0):
            """Compute expected value for given distributions.

            If bernoulli distribution is 0, the expected value is infinite.
            Otherwise, the expected value is the expected value of the
            exponential distribution divided by the probability of the
            bernoulli distribution.
            """
            if bernoulli == 0:
                # If Bernoulli always blocks, expectation is infinite
                return math.inf

            # Conditional expectation
            return (1 / exponential) / bernoulli

        if self.type == "defense":
            # Defenses have no ttc
            return 0

        distribution = self.ttc["name"]
        e = math.nan
        if distribution == "EasyAndCertain":
            e = expected_value(exponential=1.0)
        elif distribution == "EasyAndUncertain":
            e = expected_value(exponential=1.0, bernoulli=0.5)
        elif distribution == "HardAndCertain":
            e = expected_value(exponential=0.1)
        elif distribution == "HardAndUncertain":
            e = expected_value(exponential=0.1, bernoulli=0.5)
        elif distribution == "VeryHardAndCertain":
            e = expected_value(exponential=0.01)
        elif distribution == "VeryHardAndUncertain":
            e = expected_value(exponential=0.01, bernoulli=0.5)
        elif distribution == "Exponential":
            scale = float(self.ttc["arguments"][0])
            e = expected_value(exponential=scale)
        else:
            raise ValueError(f"Unknown TTC distribution: {distribution}")
        return e

    @property
    def full_name(self) -> str:
        """
        Return the full name of the attack step. This is a combination of the
        asset name to which the attack step belongs and attack step name
        itself.
        """
        if self.model_asset:
            full_name = self.model_asset.name + ':' + self.name
        else:
            full_name = str(self.id) + ':' + self.name
        return full_name


    @cached_property
    def info(self) -> dict[str, str]:
        return self.lg_attack_step.info
