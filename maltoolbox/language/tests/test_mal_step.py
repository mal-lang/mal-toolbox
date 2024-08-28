from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the OR-step `|` instruction in MAL.
'''

import os

def test_step_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines steps with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | step1
            | step2
            | step3
        } 
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_step_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines steps with same name and other type.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | step1
            & step1
        } 
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )


def test_step_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines steps with same name and same type.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | step1
            | step1
        } 
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_step_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | step1
            -> step3
            | step2
            -> step3
            | step3
        } 
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_step_5() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | guessPassword
            +> authenticate
            | stealPassword
            -> authenticate
        } 
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )


def test_step_6() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
            -> logKeystrokes
        }

        asset Linux
        {
        | spyware
            +> readBashHistory
        }
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_step_7() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
        | spyware
        }

        asset Linux
        {
        & spyware
        }
    } 
                                        
    ''').test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_step_8() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset OperatingSystem
        {
            | obtainPassword
            -> authenticate
            | obtainMFAToken
            -> authenticate
            & authenticate
        }
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem']
    )

def test_step_9() -> None:
    path = "./generated_test_mal.mal"
    with open(path, 'w') as file:
        file.write('''
        category System {
            asset OperatingSystem {
            | spyware
                -> logKeystrokes
            }
        } 
        ''')
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    include "./generated_test_mal.mal"
                        
    category System {
        asset Linux {
        | spyware
            +> readBashHistory
        }
    } 
                           
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

    if os.path.exists(path):
        os.remove(path)

def test_step_10() -> None:
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Linux {
        E hasCamera
        <- hardware[Camera]
        -> hijackCamera
        }
    } 
                           
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux']
    )