from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the Risk type (C, I, A) instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/risk_type_test_files"], indirect=True)

def test_risk_type_1() -> None:
    '''
    Defines risk types correctly
    '''
    AnalyzerTestWrapper(
        test_file="test_risk_type_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST']
    )

def test_risk_type_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines risk types. 
    define I twice
    '''
    AnalyzerTestWrapper(
        test_file="test_risk_type_2.mal"
    ).test(
        warn=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST']
    )

def test_risk_type_3() -> None:
    '''
    Defines CIA for an existance step 
    '''
    AnalyzerTestWrapper(
        test_file="test_risk_type_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST','Mock']
    )

def test_risk_type_4() -> None:
    '''
    Defines CIA for a defense step 
    '''
    AnalyzerTestWrapper(
        test_file="test_risk_type_4.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['CIA_TEST','Mock']
    )

