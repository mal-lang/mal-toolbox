from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the Risk type (C, I, A) instruction in MAL.
'''

def test_user_info_1() -> None:
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
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST']
    )





