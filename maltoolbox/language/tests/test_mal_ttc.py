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

# TESTS FOR PARETO

def test_ttc_22() -> None:
    '''
    Test correct Pareto
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_22.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_23() -> None:
    '''
    Test Pareto with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_23.mal",
        error_msg = "Expected exactly two parameters (min, shape), for Pareto distribution"
    )

def test_ttc_24() -> None:
    '''
    Test Pareto with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_24.mal",
        error_msg = "Expected exactly two parameters (min, shape), for Pareto distribution"
    )

def test_ttc_25() -> None:
    '''
    Test Pareto with invalid min 
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_25.mal",
        error_msg = "0 is not in valid range 'min > 0', for Pareto distribution"
    )

def test_ttc_26() -> None:
    '''
    Test Pareto with invalid shape 
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_26.mal",
        error_msg = "0 is not in valid range 'shape > 0', for Pareto distribution"
    )

# TESTS FOR TRUNCATEDNORMAL

def test_ttc_27() -> None:
    '''
    Test correct TruncatedNormal
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_27.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_28() -> None:
    '''
    Test TruncatedNormal with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_28.mal",
        error_msg = "Expected exactly two parameters (mean, standardDeviation), for TruncatedNormal distribution"
    )

def test_ttc_29() -> None:
    '''
    Test TruncatedNormal with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_29.mal",
        error_msg = "Expected exactly two parameters (mean, standardDeviation), for TruncatedNormal distribution"
    )

def test_ttc_30() -> None:
    '''
    Test TruncatedNormal with invalid standard deviation
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_30.mal",
        error_msg = "0 is not in valid range 'standardDeviation > 0', for TruncatedNormal distribution"
    )

# TESTS FOR UNIFORM

def test_ttc_31() -> None:
    '''
    Test correct Uniform
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_31.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_32() -> None:
    '''
    Test Uniform with more than two parameters
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_32.mal",
        error_msg = "Expected exactly two parameters (min, max), for Uniform distribution"
    )

def test_ttc_33() -> None:
    '''
    Test Uniform with one parameter
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_33.mal",
        error_msg = "Expected exactly two parameters (min, max), for Uniform distribution"
    )

def test_ttc_34() -> None:
    '''
    Test Uniform with min greater than max
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_34.mal",
        error_msg = "(5.0, 4.0) does not meet requirement 'min <= max', for Uniform distribution"
    )

# TESTS FOR COMBINATIONS
def test_ttc_35() -> None:
    '''
    Test correct Infinity 
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_35.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_36() -> None:
    '''
    Test incorrect Infinity
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_36.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_37() -> None:
    '''
    Test correct Zero
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_37.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_38() -> None:
    '''
    Test incorrect Zero
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_38.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_39() -> None:
    '''
    Test correct EasyAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_39.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_40() -> None:
    '''
    Test incorrect EasyAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_40.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_41() -> None:
    '''
    Test correct EasyAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_41.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_42() -> None:
    '''
    Test incorrect EasyAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_42.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_43() -> None:
    '''
    Test correct HardAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_43.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_44() -> None:
    '''
    Test incorrect HardAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_44.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_45() -> None:
    '''
    Test correct HardAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_45.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_46() -> None:
    '''
    Test incorrect HardAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_46.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_47() -> None:
    '''
    Test correct VeryHardAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_47.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_48() -> None:
    '''
    Test incorrect VeryHardAndCertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_48.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_49() -> None:
    '''
    Test correct VeryHardAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_49.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_50() -> None:
    '''
    Test incorrect VeryHardAndUncertain
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_50.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_51() -> None:
    '''
    Test correct Enabled
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_51.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_52() -> None:
    '''
    Test incorrect Enabled
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_52.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )

def test_ttc_53() -> None:
    '''
    Test correct Disabled
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_53.mal",
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1']
    )

def test_ttc_54() -> None:
    '''
    Test incorrect Disabled
    '''
    AnalyzerTestWrapper(
        test_file="test_ttc_54.mal",
        error_msg = "Expected exactly zero parameters, for combination distributions"
    )