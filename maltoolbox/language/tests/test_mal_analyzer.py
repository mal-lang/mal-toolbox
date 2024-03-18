import pytest

from antlr4 import InputStream, CommonTokenStream
from lexer_parser.mal_lexer import malLexer
from lexer_parser.mal_parser import malParser
from lexer_parser.mal_visitor import malVisitor
from lexer_parser.mal_analyzer import malAnalyzer

class MockCompiler():
    def __init__(self):
        self.path = None
        self.current_file = None

def compile_text(analyzer: malAnalyzer, input_string: str):
    '''
    A function to test the compiler flow with data from a string.
    '''
    input_stream = InputStream(input_string)
    lexer = malLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = malParser(stream)
    tree = parser.mal()
    compiler = MockCompiler()
    return malVisitor(compiler=compiler,  analyzer=analyzer).visit(tree)

def test_construct():
    analyzer = malAnalyzer()
    assert analyzer.has_error() == False

def test_full_flow_empty():
    analyzer = malAnalyzer()
    result = compile_text(analyzer, "")
    assert analyzer.has_error() == True

def test_full_flow_missing_define_id():
    analyzer = malAnalyzer()
    input = """
    #version:"0.0.0"
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True
    defines = list(analyzer._defines.keys())
    assert defines == ['version']

def test_full_flow_missing_define_version():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True
    defines = list(analyzer._defines.keys())
    assert defines == ['id']

def test_full_flow_wrong_format_version():
    '''
    The analyzer will add 'version' to the define-dict,
    but will fail during the post-analyzer stage.
    '''
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"version1"
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True
    defines = list(analyzer._defines.keys())
    assert defines == ['id', 'version']

def test_full_flow_correct_require_defines():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False
    defines = list(analyzer._defines.keys())
    assert defines == ['id', 'version']

def test_full_flow_prev_def_defines():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    #version:"1.0.0"
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True
    defines = list(analyzer._defines.keys())
    assert defines == ['id', 'version']

def test_full_flow_category_missing_name():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category {

    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_correct_category():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {

    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False

def test_full_flow_prev_def_asset_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
        asset Test {}
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_prev_def_asset_2():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {asset Test {}}
    category System {asset Test {}}
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True
    defines = list(analyzer._defines.keys())
    assert defines == ['id', 'version']

def test_full_flow_correct_asset():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System { 
        asset Test {
        
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False

def test_full_flow_prev_def_category_meta_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
    User: "Owner"
    User: "Borrow"
    {}
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_prev_def_category_meta_2():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
      User: "Owner"
    {}
    category System 
      User: "Borrow"
    {}
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_prev_def_asset_meta_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
    {
        asset Test 
          User: "Owner"
          User: "Borrow" 
        {}
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_prev_def_asset_meta_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
    {
        asset Test 
          User: "Borrow" 
        {}
    }

    category System 
    {
        asset Test 
          User: "Owner"
        {}
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True


def test_full_flow_prev_def_asset_meta_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System 
    {
        asset Test 
        {
        | Attack
          User: "Attacking"
          User: "Looking"
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_ok_meta():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System
      User: "Owner" 
    {
        asset Network 
          User: "Owner"
        {
        | Attack
          User: "Attacking" 
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False

def test_full_flow_extends():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    
    category Systems {
      asset Foo1 extends Foo2 {}
    }
    """
    with pytest.raises(SyntaxError):
        result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_circular_dependency():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    
    // Test Circular Dependency
    category Systems {
      asset Foo1 extends Foo2 {}
      asset Foo2 extends Foo3 {}
      asset Foo3 extends Foo4 {}
      asset Foo4 extends Foo5 {}
      asset Foo5 extends Foo1 {}
    }
    """
    with pytest.raises(Exception):
        result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_CIA_fail():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    
    category Systems {
        asset CIA_TEST 
        {
        | readOnly {C}
        | readAndAppend {C, I, I}
        | fullAccess {C, I, A}
        } 
    } 
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_CIA_defense_fail():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    
    category Systems {
        asset CIA_TEST 
        {
        # readOnly {C}
        } 
    } 
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True


def test_full_flow_CIA_OK():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    
    category Systems {
        asset CIA_TEST 
        {
        | readOnly {C}
        | readAndAppend {C, I}
        | fullAccess {C, I, A}
        } 
    } 
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False

def test_full_flow_var_1():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = hardware
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False

def test_full_flow_var_2():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = hardware
            let components = software
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_var_2():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = hardware
        }
    }
    category System {
        asset Computer {
            let components = software
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == True

def test_full_flow_var_3():
    analyzer = malAnalyzer()
    input = """
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = software \\/ hardware
        }
    }
    """
    result = compile_text(analyzer, input)
    assert analyzer.has_error() == False