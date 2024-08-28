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

def test_user_info_3() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"
                        
    category Example
    user info: "The 'Example' category contains example assets"
    {
    asset Asset1
        modeler info: "Connect the attacker to this asset"
    {
        | attack
        modeler info: "This should be the entry point for the attacker"
        developer info: "This attack step is used to reach compromise on all sub assets"
        -> subAsset*.compromise
        | compromise
        user info: "The attacker has full access on this asset"
    }
    }

    associations {
    Asset1 [superAsset] 0..1 <-- Hierarchy --> 0..1 [subAsset] Asset1
        user info: "Assets can be connected in a hierarchy"
    }
    ''').test(
        defines=['id', 'version'],
        categories=['Example'],
        assets=['Asset1']
    )