from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the `user info` instruction in MAL.
'''

def test_user_info_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines user info.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
        user info: "Hello"
        {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_user_info_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines user info twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo
        user info: "Hello"
        user info: "Hello"
        {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )