from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test Time To Compromise (TTC) expressions in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/ttc_test_files/"], indirect=True)

def test_ttc_1() -> None:
    '''
    Test correct Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_2() -> None:
    '''
    Test Bernoulli with more than one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_2.mal",
        error_msg="Expected exactly one parameter (probability), for Bernoulli distribution"
    )

def test_ttc_3() -> None:
    '''
    Test Bernoulli without parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_3.mal",
        error_msg="Expected exactly one parameter (probability), for Bernoulli distribution"
    )

def test_ttc_4() -> None:
    '''
    Test Bernoulli with invalid parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_4.mal",
        error_msg="2.0 is not in valid range '0 <= probability <= 1', for Bernoulli distribution"
    )