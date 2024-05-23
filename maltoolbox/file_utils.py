"""Utily functions for file handling"""

import json
import yaml
from python_jsonschema_objects.literals import LiteralValue

def save_dict_to_json_file(filename, serialized_object):
    """Save serialized object to a json file.

    Arguments:
    filename        - the name of the output file
    data            - dict to output as json
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serialized_object, f, indent=4)


def save_dict_to_yaml_file(filename, serialized_object):
    """Save serialized object to a yaml file.

    Arguments:
    filename        - the name of the output file
    data            - dict to output as yaml
    """
    # Handle Literal values from jsonschema_objects
    yaml.add_multi_representer(
        LiteralValue,
        lambda dumper, data: dumper.represent_data(data._value),
        yaml.SafeDumper
    )

    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(serialized_object, f, Dumper=yaml.SafeDumper)


def load_dict_from_yaml_file(filename):
    """Open json file and read as dict"""
    with open(filename, 'r', encoding='utf-8') as file:
        object_dict = yaml.safe_load(file)
    return object_dict


def load_dict_from_json_file(filename):
    """Open yaml file and read as dict"""
    with open(filename, 'r', encoding='utf-8') as file:
        object_dict = json.loads(file.read())
    return object_dict


def save_dict_to_file(filename, dictionary):
    """Save serialized object to json or yaml file.

    Arguments:
    filename        - the name of the output file
    """
    if filename.endswith(('.yml', '.yaml')):
        save_dict_to_yaml_file(filename, dictionary)
    elif filename.endswith('.json'):
        save_dict_to_json_file(filename, dictionary)
    else:
        raise ValueError('Unknown file extension, expected json/yml/yaml')
