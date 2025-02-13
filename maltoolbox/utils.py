"""Various generic classes and methods."""
import operator
from typing import Any, Dict, TypeVar

K = TypeVar("K")
V = TypeVar("V")

class LookupDict(Dict[K, V]):
    """
    A dict subclass that provides lookup functionality based on object attributes.
    
    Maintains an internal index to optimize repeated lookups based on a specific key.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the LookupDict with optional initial dictionary data.
        
        Arguments should be passes similar to `dict()`.
        
        Args:
            *args: Positional arguments passed to the base dictionary.
            **kwargs: Keyword arguments passed to the base dictionary.
        """
        super().__init__(*args, **kwargs)
        self._indices = {}

    def __setitem__(self, key, value):
        """
        Set an item in the dictionary and clear all cached indices.
        
        Args:
            key (K): The key under which the value is stored.
            value (V): The value to store.
        """
        super().__setitem__(key, value)
        self._indices.clear()

    def __delitem__(self, key):
        """
        Delete an item from the dictionary and clear all cached indices.
        
        Args:
            key (K): The key to delete.
        """
        super().__delitem__(key)
        self._indices.clear()

    def lookup(self, key: str, value: Any, op: str ="eq") -> set[Any]:
        """
        Perform a lookup in the dictionary based on an attribute and a comparison operation.
        
        Args:
            key (str): The attribute name to look up within the stored values.
            value (Any): The value to compare against.
            op (str, optional): The comparison operator (default: "eq").
                Supported operators include "eq", "in", and others from the `operator` module.
        
        Returns:
            set[Any]: A set of matching values from the dictionary.
        
        Raises:
            ValueError: If an invalid operator is provided.
        """
        if key not in self._indices:
            self._indices[key] = {getattr(v, key): set() for v in self.values()}
            for v in self.values():
                if not (vkey := getattr(v, key)) in self._indices[key].keys():
                    self._indices[key][vkey] = set()
                self._indices[key][vkey].add(v)

        if op == "eq":
            try:
                return self._indices[key][value]
            except KeyError:
                return set()

        if op == "in":
            oper = lambda a, b: operator.contains(b, a)
        else:
            try:
                oper = getattr(operator, op)
            except AttributeError:
                raise ValueError(f"Invalid operator {op}")

        ret = set()
        for i in filter(lambda k: oper(k, value), self._indices[key]):
            ret.update(self._indices[key][i])

        return ret

    def fetch(self, key: str, value: Any, op: str ="eq") -> Any:
        """
        Fetch a single matching item from the dictionary.
        
        If multiple items match, an exception is raised. If you expect
        multiple matches use `lookup()` instead.
        
        Args:
            key (str): The attribute name to look up within the stored values.
            value (Any): The value to compare against.
            op (str, optional): The comparison operator (default: "eq").
                Supported operators include "eq", "in", and others from the `operator` module.
        
        Returns:
            Any: The matching item if one is found, otherwise `None`.
        
        Raises:
            ValueError: If multiple matching items are found.
        """
        ret = self.lookup(key, value, op)

        if len(ret) > 1:
            raise ValueError(f"Multiple items match {key} ~ {op} ~ {value}")

        try:
            return next(iter(ret))
        except KeyError:
            return None
