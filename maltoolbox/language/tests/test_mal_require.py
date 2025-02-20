from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

# This file aims to test the require operator (<-) in MAL. Since a lot of it is already tested in the `exists` test file,
# the objective is to test if the general functionality is working (much like the tests for reaches (->))

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/require_test_files"], indirect=True)

def test_require_1() -> None:
    '''
    Test require correctly 
    '''
    AnalyzerTestWrapper(
        test_file='test_require_1.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3']
    )

def test_require_2() -> None:
    '''
    Test require correctly with many assets required
    '''
    AnalyzerTestWrapper(
        test_file='test_require_2.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3']
    )

def test_require_3() -> None:
    '''
    Test require with non-existing asset 
    '''
    AnalyzerTestWrapper(
        test_file='test_require_3.mal'
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3']
    )

def test_require_4() -> None:
    '''
    Test require with asset from parent's association
    '''
    AnalyzerTestWrapper(
        test_file='test_require_4.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3', 'Asset0']
    )

def test_require_5() -> None:
    '''
    Test require with asset from child's association
    '''
    AnalyzerTestWrapper(
        test_file='test_require_5.mal'
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3', 'Asset0']
    )

def test_require_6() -> None:
    '''
    Test require pointing to attack step
    '''
    AnalyzerTestWrapper(
        test_file='test_require_6.mal'
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3']
    )

def test_require_7() -> None:
    '''
    Test require using complex expression
    '''
    AnalyzerTestWrapper(
        test_file='test_require_7.mal'
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Computer', 'OperatingSystem', 'Linux', 'Windows', 'WindowsVista', 
        'FileSystem', 'SubFolder', 'Folder', 'File', 'ConfigFile', 'RootFile', 'NonRootFile']
    )