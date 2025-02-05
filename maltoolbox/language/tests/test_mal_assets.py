from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

import os

'''
A file to test different cases of the `asset` instruction in MAL.
'''

def test_assets_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset without name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System']
    )

def test_assets_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
        asset Test {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
    }
    category System {
        asset Test {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_5() -> None:
    '''
    Defines same asset in different categories
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test {}
    }
    category AnotherSystem {
        asset Test {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System', 'AnotherSystem'],
        assets=['Test']
    )

def test_assets_6() -> None:
    '''
    Defines assets correctly in different files
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #version:"0.0.0"
        #id: "org.mal-lang.testAnalyzer"

        category AnotherSystem {
            asset AnotherTest {}
        }
        ''')

    AnalyzerTestWrapper('''
    include "'''+path+'''"

    category System {
        asset Test {}
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Test','AnotherTest'],
    )

    if os.path.exists(path):
        os.remove(path)

def test_assets_7() -> None:
    '''
    Defines same asset in different files in different categories
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #version:"0.0.0"
        #id: "org.mal-lang.testAnalyzer"

        category AnotherSystem {
            asset Test {}
        }
        ''')

    AnalyzerTestWrapper('''
    include "'''+path+'''"

    category System {
        asset Test {}
    }
    ''').test(
        error= True,
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Test'],
    )

    if os.path.exists(path):
        os.remove(path)

def test_assets_8() -> None:
    '''
    Defines same asset in different files in same category
    '''
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        #version:"0.0.0"
        #id: "org.mal-lang.testAnalyzer"

        category System {
            asset Test {}
        }
        ''')

    AnalyzerTestWrapper('''
    include "'''+path+'''"

    category System {
        asset Test {}
    }
    ''').test(
        error= True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test'],
    )

    if os.path.exists(path):
        os.remove(path)
