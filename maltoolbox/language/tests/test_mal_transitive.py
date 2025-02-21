from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test the transitive step (X*.A) in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/transitive_test_files"], indirect=True)

def test_transitive_1() -> None:
    '''
    Correctly define a transitive expression (in a step)
    '''
    AnalyzerTestWrapper(
        test_file="test_transitive_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_2() -> None:
    '''
    Correctly define a transitive expression (in a variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_transitive_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_3() -> None:
    '''
    Create a transitive expression when there is no inheritance 
    relationship between X and A (A is not a child of X, given X.A*)
    '''
    AnalyzerTestWrapper(
        test_file="test_transitive_3.mal",
        error_msg="Variable 'recursive_subfolders' defined at 7 does not point to an asset"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )

def test_transitive_4() -> None:
    '''
    Test transitive step in a long hierarchy
    '''
    AnalyzerTestWrapper(
        test_file="test_transitive_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'FileSystem', 'FileSystemEntries', 'Folder', 'SubFolder']
    )

def test_transitive_5() -> None:
    '''
    Define a transitive expression, but call it without a step belonging to the asset
    '''
    AnalyzerTestWrapper(
        test_file="test_transitive_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Folder', 'SubFolder']
    )