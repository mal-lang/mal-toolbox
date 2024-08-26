from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `category` instruction in MAL.
'''

def test_category_1() -> None:
    '''
    Defines correct version and ID.
    Defines category without name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category {}
                                        
    ''').test(
        error=True,
        defines=['id', 'version']
    )

def test_category_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category Test {}
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['Test']
    )

def test_category_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with same name twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category Test {}
    category Test {}
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['Test']
    )