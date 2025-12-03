from tree_sitter import Language, Parser
import tree_sitter_mal as ts_mal

MAL_LANGUAGE = Language(ts_mal.language())
PARSER = Parser(MAL_LANGUAGE)
