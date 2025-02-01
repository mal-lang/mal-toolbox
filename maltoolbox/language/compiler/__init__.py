#!/usr/bin/env python
# mypy: ignore-errors

import os

from antlr4 import CommonTokenStream, FileStream

from .mal_lexer import malLexer
from .mal_parser import malParser
from .mal_visitor import malVisitor


class MalCompiler:
    def __init__(self) -> None:
        self.path = None
        self.current_file = None

    def compile(self, malfile: str | None = None):
        if not self.path:
            self.path = os.path.dirname(malfile)

        self.current_file = os.path.basename(malfile)

        input_stream = FileStream(
            os.path.join(self.path, self.current_file), encoding='utf-8'
        )
        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()

        return malVisitor(compiler=self).visit(tree)
