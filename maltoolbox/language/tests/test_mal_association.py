from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `association` instruction in MAL.
'''

def test_association_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines two asset with name.
    Defines an association between the assets.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {}
        asset Asset2 {}
    }
    associations {
        Asset1 [foo] * <-- connects --> * [bar] Asset2
    }                
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1', 'Asset2']
    )

def test_association_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines one asset with name.
    Defines an association between the asset 
    and one undefined right asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {}
    }
                        
    associations {
        Asset1 [foo] * <-- connects --> * [bar] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_association_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines one asset with name.
    Defines an association between the asset 
    and one undefined left asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset2 {}
    }
    associations {
        Asset1 [foo] * <-- connects --> * [bar] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset2']
    )


def test_association_4() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category Example {
        asset Asset1 
        {
            | compromise
            -> b.compromise
        }
        asset Asset2 
        {
            | compromise
        }
    }
    associations 
    {
        Asset1 [a] * <-- L --> * [b] Asset2
    }               
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['Example'],
        assets=['Asset1', 'Asset2']
    )

def test_association_5() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category Example {
        asset Asset1 
        {
            | compromise
            -> b.compromise
        }
        asset Asset2 
        {
            | compromise
        }
    }
    associations 
    {
        Asset1 [a] * <-- L --> * [c] Asset2
    }               
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['Example'],
        assets=['Asset1', 'Asset2']
    )