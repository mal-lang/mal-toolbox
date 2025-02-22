from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

# This file aims to test the append operator (+>) in MAL. Since a lot of it is already tested in the `steps` test file,
# the objective is to test if the general functionality is working (much like the tests for reaches (->))

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/append_test_files"], indirect=True)

def test_append_1() -> None:
    '''
    Test append correctly 
    '''
    AnalyzerTestWrapper(
        test_file='test_append_1.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server']
    )

def test_append_2() -> None:
    '''
    Test append correctly with many steps appended
    '''
    AnalyzerTestWrapper(
        test_file='test_append_2.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server']
    )

def test_append_3() -> None:
    '''
    Test append with wrong steps 
    '''
    AnalyzerTestWrapper(
        test_file='test_append_3.mal',
        error_msg="Attack step 'WRONG_ATTACK_STEP' not defined for asset 'Server'"
    )

def test_append_4() -> None:
    '''
    Test append with attack step from parent
    '''
    AnalyzerTestWrapper(
        test_file='test_append_4.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'Machine', 'Lenovo', 'Server']
    )

def test_append_5() -> None:
    '''
    Test append with attack step from child
    '''
    AnalyzerTestWrapper(
        test_file='test_append_5.mal',
        error_msg="Attack step 'lenovoStep' not defined for asset 'Computer'"
    )

def test_append_6() -> None:
    '''
    Test append not pointing to attack step 
    '''
    AnalyzerTestWrapper(
        test_file='test_append_6.mal',
        error_msg="Attack step 'server' not defined for asset 'Computer'"
    )

def test_append_7() -> None:
    '''
    Test append to a child's step
    '''
    AnalyzerTestWrapper(
        test_file='test_append_7.mal',
        error_msg="Cannot inherit attack step 'lenovoStep' without previous definition"
    )
