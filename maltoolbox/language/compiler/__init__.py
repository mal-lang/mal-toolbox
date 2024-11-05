#!/usr/bin/env python
# mypy: ignore-errors

import os
import sys
from typing import Optional

from antlr4 import FileStream, CommonTokenStream
from antlr4.error.ErrorListener import ConsoleErrorListener
from .mal_lexer import malLexer
from .mal_parser import malParser
from .mal_visitor import malVisitor


def patched_antrl_syntax_error(self, recognizer, offendingSymbol, line, column, msg, e):
    file = patched_antrl_syntax_error.file
    print(f"{file}:{str(line)}:{str(column)}: {msg}", file=sys.stderr)


ConsoleErrorListener.syntaxError = patched_antrl_syntax_error


class MalCompiler:
    def __init__(self):
        self.path = None
        self.current_file = None

    def compile(self, malfile: Optional[str] = None):
        if not self.path:
            self.path = os.path.dirname(malfile)

        self.current_file = os.path.basename(malfile)
        patched_antrl_syntax_error.file = malfile

        input_stream = FileStream(
            os.path.join(self.path, self.current_file), encoding="utf-8"
        )

        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()

        return malVisitor(compiler=self).visit(tree)
