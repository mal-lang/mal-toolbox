from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test Time To Compromise (TTC) expressions in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/ttc_test_files/"], indirect=True)

# TESTS FOR BERNOULLI

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

# TESTS FOR BINOMIAL

def test_ttc_5() -> None:
    '''
    Test correct Binomial
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_5.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_6() -> None:
    '''
    Test Binomial with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_6.mal",
        error_msg="Expected exactly two parameters (trials, probability), for Binomial distribution"
    )

def test_ttc_7() -> None:
    '''
    Test Binomial with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_7.mal",
        error_msg="Expected exactly two parameters (trials, probability), for Binomial distribution"
    )

def test_ttc_8() -> None:
    '''
    Test Binomial with invalid parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_8.mal",
        error_msg="2.0 is not in valid range '0 <= probability <= 1', for Binomial distribution"
    )

# TESTS FOR EXPONENTIAL

def test_ttc_9() -> None:
    '''
    Test correct Exponential
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_9.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_10() -> None:
    '''
    Test Exponential with more than one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_10.mal",
        error_msg = "Expected exactly one parameter (lambda), for Exponential distribution"
    )

def test_ttc_11() -> None:
    '''
    Test Exponential without parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_11.mal",
        error_msg = "Expected exactly one parameter (lambda), for Exponential distribution"
    )

def test_ttc_12() -> None:
    '''
    Test Exponential with invalid parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_12.mal",
        error_msg = "0 is not in valid range 'lambda > 0', for Exponential distribution"
    )

# TESTS FOR GAMMA

def test_ttc_13() -> None:
    '''
    Test correct Gamma
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_13.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_14() -> None:
    '''
    Test Gamma with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_14.mal",
        error_msg = "Expected exactly two parameters (shape, scale), for Gamma distribution"
    )

def test_ttc_15() -> None:
    '''
    Test Gamma with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_15.mal",
        error_msg = "Expected exactly two parameters (shape, scale), for Gamma distribution"
    )

def test_ttc_16() -> None:
    '''
    Test Gamma with invalid first parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_16.mal",
        error_msg = "0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_ttc_17() -> None:
    '''
    Test Gamma with invalid second parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_17.mal",
        error_msg = "0 is not in valid range 'scale > 0', for Gamma distribution"
    )

# TESTS FOR LOGNORMAL

def test_ttc_18() -> None:
    '''
    Test correct LogNormal
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_18.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_19() -> None:
    '''
    Test LogNormal with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_19.mal",
        error_msg = "Expected exactly two parameters (mean, standardDeviation), for LogNormal distribution"
    )

def test_ttc_20() -> None:
    '''
    Test LogNormal with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_20.mal",
        error_msg = "Expected exactly two parameters (mean, standardDeviation), for LogNormal distribution"
    )

def test_ttc_21() -> None:
    '''
    Test LogNormal with invalid standardDeviation
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_21.mal",
        error_msg = "0 is not in valid range 'standardDeviation > 0', for LogNormal distribution"
    )