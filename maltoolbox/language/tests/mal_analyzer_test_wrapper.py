
from antlr4 import FileStream, InputStream, CommonTokenStream

from lexer_parser.mal_lexer import malLexer
from lexer_parser.mal_parser import malParser
from lexer_parser.mal_visitor import malVisitor
from lexer_parser.mal_analyzer import malAnalyzer
from lexer_parser.mal_analyzer import malAnalyzerException

import os
import pytest
import re
from pathlib import Path

class MockCompiler():
    def __init__(self, analyzer: malAnalyzer):
        self._analyzer = analyzer
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
        return malVisitor(compiler=self, analyzer=self._analyzer).visit(tree)

class AnalyzerTestWrapper(malAnalyzer):
    def __init__(self, input_string: str = None, test_file: str = None, error_msg: str = None) -> None:
        super().__init__()

        if test_file and Path(test_file).exists():
            with open(test_file,"r") as file:
                input_string = file.read()

        input_stream = InputStream(input_string)
        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()
        compiler = MockCompiler(self)
        try:
            if error_msg:
                with pytest.raises(malAnalyzerException, match=re.escape(error_msg)):
                    self._result = malVisitor(compiler=compiler,  analyzer=self).visit(tree)
            else:
                self._result = malVisitor(compiler=compiler,  analyzer=self).visit(tree)
        except SyntaxError:
            self._error = True
        except RuntimeError:
            self._error = True
    
    def test(self, 
        error:bool=False, 
        warn:bool=False,
        defines:list=[], 
        categories:list=[], 
        assets:list=[], 
        lets:list=[], 
        associations:list=[],
        steps: list=[]):
        assert(self.has_error() == error)
        if (warn):
            assert(self.has_warning() == warn)
        if (defines):
            assert(set(defines) == set(self._defines.keys()))
        if (categories):
            assert(set(categories) == set(self._category.keys()))
        if (assets):
            assert(set(assets) == set(self._assets.keys()))
        if (lets):
            assert(set(self._vars.keys())==set([asset for asset, _ in lets]))
            for asset, variables in lets:
                assert(set(variables)==set(self._vars[asset].keys()))
        if (associations):
            assert(set(self._associations.keys())==set([asset for asset, _ in associations]))
            for asset, association_list in associations:
                assert(set(association_list)==set(self._associations[asset].keys()))
        if (steps):
            assert(set(self._steps.keys())==set([asset for asset, _ in steps]))
            for asset, step_list in steps:
                assert(set(step_list)==set(self._steps[asset].keys()))
