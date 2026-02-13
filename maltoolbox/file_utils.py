"""Utilty functions for file handling"""

import json
import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlparse
import yaml


def download_git_repo(git_url: str):
    """Clone a git repository into ./langs/<repository-name>, overriding any existing copy."""
    base_dir = Path("./.langs")

    # Derive repository name from URL
    repo_name = Path(urlparse(git_url).path).stem
    repo_dir = base_dir / repo_name

    # Ensure ./langs directory exists
    base_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing repository if present
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    # Clone repository into ./langs/<repository-name> (shallow clone)
    subprocess.run(
        ["git", "clone", "--depth", "1", git_url, str(repo_dir)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return repo_dir

def save_dict_to_json_file(filename: str, serialized_object: dict) -> None:
    """Save serialized object to a json file.

    Arguments:
    ---------
    filename        - the name of the output file
    data            - dict to output as json

    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serialized_object, f, indent=4)


def save_dict_to_yaml_file(filename: str, serialized_object: dict) -> None:
    """Save serialized object to a yaml file.

    Arguments:
    ---------
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
    with open(filename, encoding='utf-8') as file:
        object_dict = yaml.safe_load(file)
    return object_dict


def load_dict_from_json_file(filename: str) -> dict:
    """Open yaml file and read as dict"""
    with open(filename, encoding='utf-8') as file:
        object_dict = json.loads(file.read())
    return object_dict


def save_dict_to_file(filename: str, dictionary: dict) -> None:
    """Save serialized object to json or yaml file
    depending on file extension.

    Arguments:
    ---------
    filename        - the name of the output file
    dictionary      - the dict to save to the file

    """
    if filename.endswith(('.yml', '.yaml')):
        save_dict_to_yaml_file(filename, dictionary)
    elif filename.endswith('.json'):
        save_dict_to_json_file(filename, dictionary)
    else:
        raise ValueError('Unknown file extension, expected json/yml/yaml')
