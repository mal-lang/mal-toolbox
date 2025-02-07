from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

'''
A file to test different cases of the step creation in MAL, i.e. if step repetition in the same asset is detected
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
    Test if two assets with steps with the same name can exist
    '''
    AnalyzerTestWrapper('''
    #id: "org.mal-lang.testAnalyzer"
    #version:"0.0.0"

    category System {
        asset Test 
        {
            | step1
        } 
        asset AnotherTest 
        {
            | step1
        } 
    } 
                                        
    ''').test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test','AnotherTest']
    )