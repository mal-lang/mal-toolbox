from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
This file aims to test the call/substitution operator (A.X()) in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/substitution_test_files"], indirect=True)

def test_substitution_1() -> None:
    '''
    Test substitution correctly 
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_2() -> None:
    '''
    Test substitution with a non existing variable 
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_3() -> None:
    '''
    Test substitution with an existing variable, but forget to call it, i.e. do not use parenthesis
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_3.mal"
    ).test(
        error=True,
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_substitution_4() -> None:
    '''
    Try to call a variable defined in the parent
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'SubNet', 'Computer', 'OperatingSystem']
    )

def test_substitution_5() -> None:
    '''
    Try to call a variable defined in a parent in a complex hierarchy
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_5.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Hardware', 'Machine', 'Computer', 'Lenovo', 'LenovoThinkPad']
    )

def test_substitution_6() -> None:
    '''
    Try to call a variable defined in the child
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_6.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'SubNet', 'Computer', 'OperatingSystem']
    )

def test_substitution_7() -> None:
    '''
    Try to call a variable defined in another asset 
    '''
    AnalyzerTestWrapper(
        test_file="test_substitution_7.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Hardware', 'PhysicalComponent', 'Computer']
    )
