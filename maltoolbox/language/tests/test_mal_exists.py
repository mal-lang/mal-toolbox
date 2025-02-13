from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test existance operators (E and !E) in MAL
'''

def test_exists_1() -> None:
    '''
    Correctly define defenses
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        E step1
            <- a3
        !E step2
            <- a2
        }
        asset Asset2 {}
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_2() -> None:
    '''
    Test existance with a reach with a non-existing attack step
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        E step1
            <- a3
            -> wrongStep
        }
        asset Asset2 {}
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_3() -> None:
    '''
    Test existence with non-existing asset
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        E step1
            <- a2
        }
        asset Asset2 {}
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3

        //                 COMMENTED 
        //                     |
        //                     V
        //Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
    
def test_exists_4() -> None:
    '''
    Test existence with a requires which points to a step
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        !E step1
            <- a2.attack
        }
        asset Asset2 {
        & attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
    
def test_exists_5() -> None:
    '''
    Test existence with a TTC expression
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        !E step1 [Bernoulli(0.2)]
            <- a2
        }
        asset Asset2 {
        & attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_6() -> None:
    '''
    Test existence with a TTC expression
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        !E step1 [Bernoulli(0.2)]
            <- a2
        }
        asset Asset2 {
        & attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_7() -> None:
    '''
    Test existence without a requires
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        E step1 
            -> a2.attack
        }
        asset Asset2 {
        & attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_8() -> None:
    '''
    Test normal step with a requires
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {
        & step1 
            <- a2.attack
        }
        asset Asset2 {
        & attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset1 [a1] * <-- connects --> * [a2] Asset2
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
