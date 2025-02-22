from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

# This file aims to test the collect operator (X.A) in MAL

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/collect_test_files"], indirect=True)

def test_collect_1() -> None:
    '''
    Test collect correctly (used in variable)
    '''
    AnalyzerTestWrapper(
        test_file='test_collect_1.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )

def test_collect_2() -> None:
    '''
    Test collect correctly (used in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem']
    )
    
def test_collect_3() -> None:
    '''
    Test complex collect correctly (used in variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_3.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'FileSystem', 'File']
    )

def test_collect_4() -> None:
    '''
    Test complex collect correctly (used in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'FileSystem', 'File']
    )

def test_collect_5() -> None:
    '''
    Test correctly with non-existing field
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_5.mal",
        error_msg="Field 'fileSystems' not defined for asset 'OperatingSystem'\n" + \
                  "Line 6: All expressions in reaches ('->') must point to a valid attack step"
    )

# Since many tests require that collect works correctly, the objective of the following tests is to check that 
# using many expressions in the same collect works properly and any error inside the expression itself is noticed.

def test_collect_6() -> None:
    '''
    Test complex set of expressions
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_6.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )

def test_collect_7() -> None:
    '''
    Test complex set of expressions with error 
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_7.mal",
        error_msg="Asset 'WindowsVista' cannot be of type 'OperatingSystem'\n" +\
                  "Line 7: All expressions in reaches ('->') must point to a valid attack step"
    )

def test_collect_8() -> None:
    '''
    Test complex set of expressions with error (field without existing association)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_8.mal",
        error_msg="Field 'fileSystems' not defined for asset 'OperatingSystem'\n" + \
                  "Line 7: All expressions in reaches ('->') must point to a valid attack step"
    )

def test_collect_9() -> None:
    '''
    Test complex set of expressions with error (transitive step without hierarchy relationship)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_9.mal",
        error_msg="Previous asset 'Folder' is not of type 'SubFolder'\n" + \
                  "Line 7: All expressions in reaches ('->') must point to a valid attack step"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )

def test_collect_10() -> None:
    '''
    Test complex set of expressions with error (no common ancestor)
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_10.mal",
        error_msg="Types 'ConfigFile' and 'NonRootFile' have no common ancestor\n" + \
                  "Line 7: All expressions in reaches ('->') must point to a valid attack step"
    )
