# -*- encoding: utf-8 -*-
# MAL Toolbox v0.1.10
# Copyright 2024, Andrei Buhaiu.
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

__title__ = 'maltoolbox'
__version__ = '0.1.10'
__authors__ = ['Andrei Buhaiu',
    'Giuseppe Nebbione',
    'Nikolaos Kakouros',
    'Jakob Nyberg',
    'Joakim Loxdal']
__license__ = 'Apache 2.0'
__docformat__ = 'restructuredtext en'

__all__ = ()

import os
import configparser
import logging

ERROR_INCORRECT_CONFIG = 1

CONFIGFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "default.conf"
)

config = configparser.ConfigParser()
config.read(CONFIGFILE)

if 'logging' not in config:
    raise ValueError('Config file is missing essential information, cannot proceed.')

if 'log_file' not in config['logging']:
    raise ValueError('Config file is missing a log_file location, cannot proceed.')

log_configs = {
    'log_file': config['logging']['log_file'],
    'log_level': config['logging']['log_level'],
    'attackgraph_file': config['logging']['attackgraph_file'],
    'model_file': config['logging']['model_file'],
    'langspec_file': config['logging']['langspec_file'],
}

os.makedirs(os.path.dirname(log_configs['log_file']), exist_ok = True)

formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', datefmt='%m-%d %H:%M')
file_handler = logging.FileHandler(log_configs['log_file'], mode='w')
file_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

log_level = log_configs['log_level']
if log_level != '':
    level = logging.getLevelName(log_level)
    logger.setLevel(level)
    logger.info('Set loggin level of %s to %s.', __name__, log_level)

if 'neo4j' in config:
    for term in ['uri', 'username', 'password', 'dbname']:
        if term not in config['neo4j']:

            msg = (
                'Config file is missing essential Neo4J '
                f'information: {term}, cannot proceed.'
            )
            logger.critical(msg)
            raise ValueError(msg)

    neo4j_configs = {
        'uri': config['neo4j']['uri'],
        'username': config['neo4j']['username'],
        'password': config['neo4j']['password'],
        'dbname': config['neo4j']['dbname'],
    }
