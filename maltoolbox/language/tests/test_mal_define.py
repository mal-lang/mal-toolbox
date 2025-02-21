from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `define` instruction in MAL.
'''

def test_define_1() -> None:
    '''
    Defines only version.
    '''
    AnalyzerTestWrapper('''
    #version:"0.0.0"
    ''').test(
        error=True,
        defines=['version']
    )

def test_define_2() -> None:
    '''
    Defines only ID.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    ''').test(
        error=True,
        defines=['id']
    )

def test_define_3() -> None:
    '''
    Defines correct ID but wrong version.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"version1"
    ''').test(
        error=True,
        defines=['id', 'version']
    )

def test_define_4() -> None:
    '''
    Defines correct version and ID.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    ''').test(
        defines=['id', 'version']
    )

def test_define_5() -> None:
    '''
    Defines correct version and ID, but version twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    #version:"1.0.0"
    ''').test(
        defines=['id', 'version']
    )

def test_define_6() -> None:
    '''
    Defines correct version, ID.
    Defines Key with value.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    #key:"value"
    ''').test(
        defines=['id', 'version', 'key']
    )

def test_define_7() -> None:
    '''
    Defines correct version, ID.
    Defines Key with value twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    #key:"value"
    #key:"value"
    ''').test(
        error=True,
        defines=['id', 'version', 'key']
    )

def test_define_8() -> None:
    '''
    Defines correct version and ID, but id twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
    #version:"1.0.0"
    ''').test(
        defines=['id', 'version']
    )