"""Various generic classes and methods."""
import json
import operator
from typing import Any, Dict, TypeVar

import yaml

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
        self._indices: dict[str, dict] = {}

    def __setitem__(self, key, value):
        """
        Set an item in the dictionary and clear all cached indices.

        Args:
            key (K): The key under which the value is stored.
            value (V): The value to store.
        """
        super().__setitem__(key, value)

        for key in self._indices:
            self._indices[key][getattr(value, key)] = value

    def __delitem__(self, key):
        """
        Delete an item from the dictionary and clear all cached indices.

        Args:
            key (K): The key to delete.
        """
        item = self[key]

        super().__delitem__(key)

        for index in self._indices:
            del self._indices[index][getattr(item, index)]

    def lookup(self, key: str, value: Any, op: str = "eq") -> set[Any]:
        """
        Search in the dictionary based on an attribute and a comparison operation.

        Args:
            key (str): The attribute name to look up within the stored values.
            value (Any): The value to compare against.
            op (str, optional): The comparison operator (default: "eq").
                Supported operators include "eq", "in", and others from the `operator`
                module.

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
            return self._indices[key].get(value, set())

        if op == "in":
            def oper(a, b): return operator.contains(b, a)
        else:
            try:
                oper = getattr(operator, op)
            except AttributeError:
                raise ValueError(f"Invalid operator {op}")

        ret = set()
        for i in filter(lambda k: oper(k, value), self._indices[key]):
            ret.update(self._indices[key][i])

        return ret

    def fetch(self, key: str, value: Any, op: str = "eq") -> Any:
        """
        Fetch a single matching item from the dictionary.

        If multiple items match, an exception is raised. If you expect
        multiple matches use `lookup()` instead.

        Args:
            key (str): The attribute name to look up within the stored values.
            value (Any): The value to compare against.
            op (str, optional): The comparison operator (default: "eq").
                Supported operators include "eq", "in", and others from the `operator`
                module.

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


def save_dict_to_json_file(filename: str, serialized_object: dict) -> None:
    """Save serialized object to a json file.

    Arguments:
    filename        - the name of the output file
    data            - dict to output as json
    """

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serialized_object, f, indent=4)


def save_dict_to_yaml_file(filename: str, serialized_object: dict) -> None:
    """Save serialized object to a yaml file.

    Arguments:
    filename        - the name of the output file
    data            - dict to output as yaml
    """

    class NoAliasSafeDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(serialized_object, f, Dumper=NoAliasSafeDumper)


def load_dict_from_yaml_file(filename: str) -> dict:
    """Open json file and read as dict"""
    with open(filename, 'r', encoding='utf-8') as file:
        object_dict = yaml.safe_load(file)
    return object_dict


def load_dict_from_json_file(filename: str) -> dict:
    """Open yaml file and read as dict"""
    with open(filename, 'r', encoding='utf-8') as file:
        object_dict = json.loads(file.read())
    return object_dict


def save_dict_to_file(filename: str, dictionary: dict) -> None:
    """Save serialized object to json or yaml file
    depending on file extension.

    Arguments:
    filename        - the name of the output file
    dictionary      - the dict to save to the file
    """

    if filename.endswith(('.yml', '.yaml')):
        save_dict_to_yaml_file(filename, dictionary)
    elif filename.endswith('.json'):
        save_dict_to_json_file(filename, dictionary)
    else:
        raise ValueError('Unknown file extension, expected json/yml/yaml')
