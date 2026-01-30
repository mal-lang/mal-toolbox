import json
import logging
import zipfile

from maltoolbox.exceptions import LanguageGraphException
from maltoolbox.file_utils import load_dict_from_json_file, load_dict_from_yaml_file
from maltoolbox.language.compiler.mal_compiler import MalCompiler
from maltoolbox.language.languagegraph import LanguageGraph, language_graph_from_dict


logger = logging.getLogger(__name__)


