from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

# This file aims to test the reaches operator (->) in MAL

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/reaches_test_files"], indirect=True)

def test_reaches_1() -> None:
    '''
    Test reaches correctly 
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_1.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server']
    )

def test_reaches_2() -> None:
    '''
    Test many reaches in the same step
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_2.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server', 'Router']
    )

def test_reaches_3() -> None:
    '''
    Test reaches with wrong attack step
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_3.mal',
        error_msg= "Attack step 'WRONG_ATTACK_STEP' not defined for asset 'Server'"
    )

def test_reaches_4() -> None:
    '''
    Test reaches with attack step from father
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_4.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server', 'Router']
    )

def test_reaches_5() -> None:
    '''
    Test reaches with attack step from child
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_5.mal',
        error_msg="Attack step 'lenovoStep' not defined for asset 'Computer'"
    )

def test_reaches_6() -> None:
    '''
    Test reaches not pointing to attack step
    '''
    AnalyzerTestWrapper(
        test_file='test_reaches_6.mal',
        error_msg="Attack step 'routers' not defined for asset 'Network'"
    )
