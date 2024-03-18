#!/usr/bin/env python

from antlr4 import FileStream, CommonTokenStream
from .mal_lexer import malLexer
from .mal_parser import malParser
from .mal_visitor import malVisitor

import sys
import os
import json


class MalCompiler:
    def __init__(self):
        self.path = None
        self.current_file = None

    def compile(self, malfile: str = None):
        if not self.path:
            self.path = os.path.dirname(malfile)

        self.current_file = os.path.basename(malfile)

        input_stream = FileStream(
            os.path.join(self.path, self.current_file), encoding="utf-8"
        )
        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()

        return malVisitor(compiler=self).visit(tree)


if __name__ == "__main__":
    compiler = MalCompiler()

    with open("new_langspec.json", "w") as f:
        json.dump(compiler.compile(sys.argv[1]), f, indent=2)
