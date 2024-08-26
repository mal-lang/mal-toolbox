from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `abstract` instruction in MAL.
'''

def test_abstract_assets_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines abstract asset without name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        abstract asset {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System']
    )

def test_abstract_assets_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines abstract asset with name.
    Extends asset with abstract asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        abstract asset Foo {}
        asset Bar extends Foo {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo', 'Bar']
    )
