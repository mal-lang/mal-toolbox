# -*- encoding: utf-8 -*-
# MAL Toolbox v1.0.5
# Copyright 2025, Andrei Buhaiu.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""
MAL-Toolbox Framework
"""

__title__ = "maltoolbox"
__version__ = "1.0.5"
__authors__ = [
    "Andrei Buhaiu",
    "Giuseppe Nebbione",
    "Nikolaos Kakouros",
    "Jakob Nyberg",
    "Joakim Loxdal",
]
__license__ = "Apache 2.0"
__docformat__ = "restructuredtext en"

__all__ = ()

import os
import yaml
import logging
from typing import Any

config: dict[str, Any] = {
    "logging": {
        "log_level": logging.INFO,
        "log_file": "logs/log.txt",
        "attackgraph_file": "logs/attackgraph.yml",
        "model_file": "logs/model.yml",
        "langspec_file": "logs/langspec_file.json",
        "langgraph_file": "logs/langgraph.yml",
    },
}

config_file = os.getenv("MALTOOLBOX_CONFIG", "maltoolbox.yml")

if os.path.exists(config_file):
    with open(config_file) as f:
        config |= yaml.safe_load(f)

log_configs = config['logging']
os.makedirs(os.path.dirname(log_configs["log_file"]), exist_ok=True)

formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%m-%d %H:%M"
)
file_handler = logging.FileHandler(log_configs["log_file"], mode="w")
file_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

logger.setLevel(log_configs.get("log_level"))
logger.info("Set loggin level of %s to %s.", __name__, log_configs.get("log_level"))

logger.debug("Config file location: %s", config_file)
