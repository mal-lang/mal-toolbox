class MalToolboxException(Exception):
    """Base exception for all other maltoolbox exceptions to inherit from."""


class LanguageGraphException(MalToolboxException):
    """Base exception for all language-graph related exceptions."""


class LanguageGraphSuperAssetNotFoundError(LanguageGraphException):
    """Asset's super asset not found in language graph during attack graph construction."""


class LanguageGraphAssociationError(LanguageGraphException):
    """Error in building an association.

    For example, right or left-hand side asset of association missing in
    language graph.
    """


class LanguageGraphStepExpressionError(LanguageGraphException):
    """A target asset cannot be linked with for a step expression."""


class AttackGraphException(MalToolboxException):
    """Base exception for all attack-graph related exceptions."""


class AttackGraphStepExpressionError(AttackGraphException):
    """A target attack step cannot be linked with for a step expression."""


class ModelException(MalToolboxException):
    """Base Exception for all Model related exceptions"""


class ModelAssociationException(ModelException):
    """Exception related to associations in Model"""


class DuplicateModelAssociationError(ModelException):
    """Associations should be unique as part of Model"""
