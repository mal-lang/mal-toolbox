from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test existance operators (E and !E) in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/exists_test_files"], indirect=True)

def test_exists_1() -> None:
    '''
    Correctly define defenses
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_2() -> None:
    '''
    Test existance with a reach with a non-existing attack step
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_3() -> None:
    '''
    Test existence with non-existing asset
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
    
def test_exists_4() -> None:
    '''
    Test existence with a requires which points to a step
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_4.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
    
def test_exists_5() -> None:
    '''
    Test existence with a TTC expression
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_6() -> None:
    '''
    Test existence with a TTC expression
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_6.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_7() -> None:
    '''
    Test existence without a requires
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_7.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )

def test_exists_8() -> None:
    '''
    Test normal step with a requires
    '''
    AnalyzerTestWrapper(
        test_file="test_exists_8.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
    )
