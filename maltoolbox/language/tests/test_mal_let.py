from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `let` instruction in MAL.
'''

def test_let_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = software \\/ hardware
        }
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer'],
        lets=[('Computer', 'components')]
    )

def test_let_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines two assets with name.
    Defines same let twice.
    '''
    AnalyzerTestWrapper('''
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
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer'],
        lets=[('Computer', 'components')]
    )

def test_let_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines same let twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let components = hardware
            let components = software
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer'],
        lets=[('Computer', 'components')]
    )

def test_let_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines same let twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            | compromise
        }
        asset Computer {
            let var1 = asset1
            | compromise
            -> var1.compromise
        }
    }

    associations 
    {
        Computer [computer] * <-- L --> * [asset1] Asset1
    }                                    
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Asset1'],
        lets=[('Computer', 'var1')]
    )