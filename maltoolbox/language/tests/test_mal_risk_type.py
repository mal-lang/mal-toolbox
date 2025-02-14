from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the Risk type (C, I, A) instruction in MAL.
'''
def test_risk_type_1() -> None:
    '''
    Defines risk types correctly
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset CIA_TEST 
        {
        | readOnly {C}
        | readAndAppend {C, I}
        | appendAndRead {I, C}
        | fullAccess {C, I, A}
        } 
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST']
    )

def test_risk_type_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines risk types. 
    define I twice
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset CIA_TEST 
        {
        | readOnly {C}
        | readAndAppend {C, I, I}
        | fullAccess {C, I, A}
        } 
    } 
                                        
    ''').test(
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST']
    )

def test_risk_type_3() -> None:
    '''
    Defines CIA for an existance step 
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset CIA_TEST 
        {
        E step {C}
            <- mock
        } 
        
        asset Mock {
        }
    } 

    association {
        CIA_TEST [test] 1 <-- L --> 1 [mock] Mock
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST','Mock']
    )

def test_risk_type_4() -> None:
    '''
    Defines CIA for a defense step 
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset CIA_TEST 
        {
        # step {C}
        } 
        
        asset Mock {
        }
    } 

    association {
        CIA_TEST [test] 1 <-- L --> 1 [mock] Mock
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST','Mock']
    )

