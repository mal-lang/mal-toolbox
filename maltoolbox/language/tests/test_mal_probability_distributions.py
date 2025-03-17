from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test complex Time To Compromise (TTC) expressions in MAL

While 'test_mal_ttc' tests individual expressions, this file will test the same expressions 
when used together
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/probability_distributions_test_files/"], indirect=True)

# Basic exponentiation tests

def test_probability_distributions_1() -> None:
    '''
    Test correct exponentiation 
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_1.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_2() -> None:
    '''
    Test exponentiation with an expression with the wrong parameters
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_2.mal',
        error_msg="0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_probability_distributions_3() -> None:
    '''
    Test exponentiation with Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_3.mal',
        error_msg="TTC distribution 'Bernoulli' is not available in subtraction, division or exponential expressions."
    )

def test_probability_distributions_4() -> None:
    '''
    Test exponentiation with EasyAndUncertaion
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_4.mal',
        error_msg="TTC distribution 'EasyAndUncertain' is not available in subtraction, division or exponential expressions."
    )

# Basic subtraction tests

def test_probability_distributions_5() -> None:
    '''
    Test correct subtraction
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_5.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_6() -> None:
    '''
    Test subtraction with an expression with the wrong parameters
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_6.mal',
        error_msg="0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_probability_distributions_7() -> None:
    '''
    Test subtraction with Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_7.mal',
        error_msg="TTC distribution 'Bernoulli' is not available in subtraction, division or exponential expressions."
    )

def test_probability_distributions_8() -> None:
    '''
    Test subtraction with EasyAndUncertaion
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_8.mal',
        error_msg="TTC distribution 'EasyAndUncertain' is not available in subtraction, division or exponential expressions."
    )

# Basic division tests

def test_probability_distributions_9() -> None:
    '''
    Test correct division 
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_9.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_10() -> None:
    '''
    Test division with an expression with the wrong parameters
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_10.mal',
        error_msg="0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_probability_distributions_11() -> None:
    '''
    Test division with Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_11.mal',
        error_msg="TTC distribution 'Bernoulli' is not available in subtraction, division or exponential expressions."
    )

def test_probability_distributions_12() -> None:
    '''
    Test division with EasyAndUncertaion
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_12.mal',
        error_msg="TTC distribution 'EasyAndUncertain' is not available in subtraction, division or exponential expressions."
    )

# Basic addition tests

def test_probability_distributions_13() -> None:
    '''
    Test correct addition
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_13.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_14() -> None:
    '''
    Test addition with an expression with the wrong parameters
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_14.mal',
        error_msg="0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_probability_distributions_15() -> None:
    '''
    Test addition with Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_15.mal',
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

# Basic multiplication tests

def test_probability_distributions_16() -> None:
    '''
    Test correct multiplication 
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_16.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_17() -> None:
    '''
    Test multiplication with an expression with the wrong parameters
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_17.mal',
        error_msg="0 is not in valid range 'shape > 0', for Gamma distribution"
    )

def test_probability_distributions_18() -> None:
    '''
    Test multiplication with Bernoulli
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_18.mal',
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

# Complex operation tests

def test_probability_distributions_19() -> None:
    '''
    Test correct complex operation I
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_19.mal',
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_20() -> None:
    '''
    Test correct complex operation II
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_20.mal',
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_21() -> None:
    '''
    Test correct complex operation III
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_21.mal',
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_probability_distributions_22() -> None:
    '''
    Test incorrect complex operation I
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_22.mal',
        error_msg="(0.4, 0.3) does not meet requirement 'min <= max', for Uniform distribution"
    )

def test_probability_distributions_23() -> None:
    '''
    Test incorrect complex operation II
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_23.mal',
        error_msg="Distributions 'Enabled' or 'Disabled' may not be used as TTC values in '&' and '|' attack steps"
    )

def test_probability_distributions_24() -> None:
    '''
    Test incorrect complex operation III
    '''
    AnalyzerTestWrapper(
        test_file='test_probability_distributions_24.mal',
        error_msg="TTC distribution 'Bernoulli' is not available in subtraction, division or exponential expressions."
    )