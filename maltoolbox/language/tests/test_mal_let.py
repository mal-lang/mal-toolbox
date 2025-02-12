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
        asset Platform {
          | access
        }
        asset Computer {
          let components = software \\/ hardware
          | access
        }
        asset Software extends Platform {
          | compromise
        }
        asset Hardware extends Platform {
          | overheat
        }
    }
    associations {
      Computer [host] 1 <-- Programs --> * [software] Software
      Computer [host] 1 <-- SpecificHardware --> * [hardware] Hardware
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer','Platform','Software','Hardware'],
        lets=[('Computer', ['components'])]
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
        asset Platform {
          | access
        }
        asset Computer {
          let component = software 
          let component = hardware 
          | access
        }
        asset Software extends Platform {
          | compromise
        }
        asset Hardware extends Platform {
          | overheat
        }
    }
    associations {
      Computer [host] 1 <-- Programs --> * [software] Software
      Computer [host] 1 <-- SpecificHardware --> * [hardware] Hardware
    }
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer','Platform','Hardware','Software'],
        lets=[('Computer', ['component'])]
    )

def test_let_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let not pointing to asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Computer {
            let component = hardware
        }
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer'],
        lets=[('Computer', ['component'])]
    )

def test_let_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            let component = asset3
        }
        asset Asset2 extends Asset1 {
            let another_component = asset4
        }
        asset Asset3 {
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset3] Asset3
        Asset2 [asset2] 1 <-- Two --> 1 [asset4] Asset4
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2', ['component','another_component'])]
    )


def test_let_5() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Redefines let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            let component = asset3
        }
        asset Asset2 extends Asset1 {
            let component = asset4
        }
        asset Asset3 {
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset3] Asset3
        Asset2 [asset2] 1 <-- Two --> 1 [asset4] Asset4
    }
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2',['component'])]
    )

def test_let_6() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let in circular manner.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            let component1 = component2()
            let component2 = component1()
        }
        asset Asset3 {
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset3] Asset3
        Asset1 [asset1] 1 <-- Two --> 1 [asset4] Asset4
    }
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset1', ['component1','component2'])]
    )

def test_let_7() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let when a parent has no association.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        }
        asset Asset3 extends Asset1 {
            let component = asset4
        }
        asset Asset4 {
        }
    }
    associations {
        Asset3 [asset3] 1 <-- One --> 1 [asset4] Asset4
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset3', ['component'])]
    )

def test_let_8() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let using a parents association.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        }
        asset Asset3 extends Asset1 {
            let component = asset4
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset4] Asset4
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset3', ['component'])]
    )

def test_let_9() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let only in a parent.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            let component = asset4
        }
        asset Asset3 extends Asset1 {
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset4] Asset4
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset3', ['component'])]
    )
    
def test_let_10() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Redefines the exact same let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
            let component = asset3
        }
        asset Asset2 extends Asset1 {
            let component = asset3
        }
        asset Asset3 {
        }
        asset Asset4 {
        }
    }
    associations {
        Asset1 [asset1] 1 <-- One --> 1 [asset3] Asset3
    }
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2',['component'])]
    )