from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `abstract` instruction in MAL.
'''

# TODO: is this test really needed? Doesn't the grammar prevent this kind of situation?
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

def test_abstract_assets_3() -> None:
    '''
    Test if chain of abstract extentions works
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        abstract asset Foo {}
        abstract asset Bar extends Foo {}
        asset Baz extends Bar {}
    }

    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo','Bar','Baz']
    )

def test_abstract_assets_4() -> None:
    '''
    Abstract asset is never extended
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        abstract asset Foo {}
        asset Bar {}
    } 
    ''').test(
        warn=True,
        defines=['id','version'],
        categories=['System'],
        assets=['Foo','Bar']
    )