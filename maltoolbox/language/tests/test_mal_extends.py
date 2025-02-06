from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

import os

'''
A file to test different cases of the `extends` instruction in MAL.
'''

def test_extends_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines asset with extends.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem {}
        asset Linux extends OperatingSystem {}
    }
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_extends_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Extends asset with undefined asset.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo1 extends Foo2 {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo1']
    )

def test_extends_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Tests circular dependency with extends
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Foo1 extends Foo2 {}
        asset Foo2 extends Foo3 {}
        asset Foo3 extends Foo4 {}
        asset Foo4 extends Foo5 {}
        asset Foo5 extends Foo1 {}
    }
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo1', 'Foo2', 'Foo3', 'Foo4', 'Foo5']
    )


def test_extends_4() -> None:
    '''
    Tests valid extends across files
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
        asset SubTest extends Test {}
    }
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test','SubTest'],
    )

    if os.path.exists(path):
        os.remove(path)
