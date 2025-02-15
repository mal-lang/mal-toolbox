from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the step creation in MAL, i.e. if step repetition in the same asset is detected
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/step_test_files"], indirect=True)

def test_step_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines steps with name.
    '''
    AnalyzerTestWrapper(
        test_file="test_step_1.mal"
    ).test(
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
    AnalyzerTestWrapper(
        test_file="test_step_2.mal"
    ).test(
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
    AnalyzerTestWrapper(
        test_file="test_step_3.mal"
    ).test(
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
    AnalyzerTestWrapper(
        test_file="test_step_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_step_5() -> None:
    '''
    Test if two assets with steps with the same name can exist
    '''
    AnalyzerTestWrapper(
        test_file="test_step_5.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test','AnotherTest']
    )