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
        test_file="test_collect_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'FileSystem', 'File']
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
        test_file="test_collect_7.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )

def test_collect_8() -> None:
    '''
    Test complex set of expressions with error 
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_8.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )

def test_collect_9() -> None:
    '''
    Test complex set of expressions with error 
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_9.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )

def test_collect_10() -> None:
    '''
    Test complex set of expressions with error 
    '''
    AnalyzerTestWrapper(
        test_file="test_collect_10.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )