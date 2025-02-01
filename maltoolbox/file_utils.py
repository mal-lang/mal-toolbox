"""Utily functions for file handling."""

import json

import yaml
from python_jsonschema_objects.literals import LiteralValue


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
        def ignore_aliases(self, data) -> bool:
            return True

    # Handle Literal values from jsonschema_objects
    yaml.add_multi_representer(
        LiteralValue,
        lambda dumper, data: dumper.represent_data(data._value),
        NoAliasSafeDumper,
    )

    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(serialized_object, f, Dumper=NoAliasSafeDumper)


def load_dict_from_yaml_file(filename: str) -> dict:
    """Open json file and read as dict."""
    with open(filename, encoding='utf-8') as file:
        return yaml.safe_load(file)


def load_dict_from_json_file(filename: str) -> dict:
    """Open yaml file and read as dict."""
    with open(filename, encoding='utf-8') as file:
        return json.loads(file.read())


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
        msg = 'Unknown file extension, expected json/yml/yaml'
        raise ValueError(msg)
