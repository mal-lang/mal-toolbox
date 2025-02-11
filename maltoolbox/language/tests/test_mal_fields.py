from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test fields in MAL
'''

def test_fields_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines associations correctly
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {}
        asset Asset2 extends Asset1 {}
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset2 [a2] * <-- connects --> * [a3_again] Asset3
    }                
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
        associations=[('Asset1',['a3']), ('Asset2',['a3','a3_again']), ('Asset3',['a1','a2'])]
    )
    
def test_fields_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines association in child with same name as parent
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {}
        asset Asset2 extends Asset1 {}
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset2 [a2] * <-- connects --> * [a3] Asset3
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
        associations=[('Asset1',['a3']), ('Asset2',['a3']), ('Asset3',['a1','a2'])]
    )

def test_fields_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines association with same name as attack step
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Asset1 {}
        asset Asset2 extends Asset1 {
          | attack
        }
        asset Asset3 {}
    }
    associations {
        Asset1 [a1] * <-- connects --> * [a3] Asset3
        Asset2 [a2] * <-- connects --> * [attack] Asset3
    }                
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
        associations=[('Asset1',['a3']), ('Asset2',['a3']), ('Asset3',['a1','a2'])]
    )
