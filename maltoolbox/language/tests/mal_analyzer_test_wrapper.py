
from antlr4 import FileStream, InputStream, CommonTokenStream

from lexer_parser.mal_lexer import malLexer
from lexer_parser.mal_parser import malParser
from lexer_parser.mal_visitor import malVisitor
from lexer_parser.mal_analyzer import malAnalyzer

import os

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
    def __init__(self, input_string: str) -> None:
        super().__init__()
        input_stream = InputStream(input_string)
        lexer = malLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = malParser(stream)
        tree = parser.mal()
        compiler = MockCompiler(self)
        try:
            self._result = malVisitor(compiler=compiler,  analyzer=self).visit(tree)
        except SyntaxError:
            self._error = True
        except RuntimeError:
            self._error = True
    
    def test(self, error:bool=False, defines:list=[], categories:list=[], assets:list=[], lets:list=[]):
        assert(self.has_error() == error)
        if (defines):
            assert(set(defines) == set(self._defines.keys()))
        if (categories):
            assert(set(categories) == set(self._category.keys()))
        if (assets):
            assert(set(assets) == set(self._assets.keys()))
        if (lets):
            for let in lets:
                where, name = let
                if (not (self._vars[where] and self._vars[where][name])):
                    assert(False)



