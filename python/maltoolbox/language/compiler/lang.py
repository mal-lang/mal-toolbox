import tree_sitter_mal as ts_mal
from tree_sitter import Language, Parser

MAL_LANGUAGE = Language(ts_mal.language())
PARSER = Parser(MAL_LANGUAGE)
