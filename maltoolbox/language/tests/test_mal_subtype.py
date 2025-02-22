from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test the subtype expression in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/subtype_test_files"], indirect=True)

def test_subtype_1() -> None:
    '''
    Test subtype correctly (defined in variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_subtype_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_subtype_2() -> None:
    '''
    Test subtype correctly (defined in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_subtype_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_subtype_3() -> None:
    '''
    Test subtype without inheritance relationship (given X[A], a is not a child of X)
    '''
    AnalyzerTestWrapper(
        test_file="test_subtype_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_subtype_4() -> None:
    '''
    Test subtype, but with a wrong attack step
    '''
    AnalyzerTestWrapper(
        test_file="test_subtype_4.mal",
        error_msg="Attack step 'foundLinux' not defined for asset 'Windows'"
    )

def test_subtype_5() -> None:
    '''
    Test subtype in a long hierarchy
    '''
    AnalyzerTestWrapper(
        test_file="test_subtype_5.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'WindowsVista', 'WindowsVistaProfessional', 'OperatingSystem']
    )