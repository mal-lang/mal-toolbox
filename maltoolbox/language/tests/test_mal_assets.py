from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `asset` instruction in MAL.
'''

def test_assets_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset without name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System']
    )

def test_assets_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
        asset Test {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
    }
    category System {
        asset Test {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )