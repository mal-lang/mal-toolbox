from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest
import os

'''
A file to test different cases of the `include` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/include_test_files"], indirect=True)

def test_include_1() -> None:
    '''
    Missing keys ID and version.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_1.mal",
        error_msg = 'Missing required define \'#id: ""\''
    ).test(
        error=True
    )

def test_include_2() -> None:
    '''
    Including file with ID and version.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_2.mal"
    ).test(
        defines=['id', 'version']
    )

def test_include_3() -> None:
    '''
    Including file with ID and version.
    Defining ID and version both files (this is ok).
    '''
    AnalyzerTestWrapper(
        test_file="test_include_3.mal"
    ).test(
        defines=['id', 'version']
    )
        
def test_include_4() -> None:
    '''
    Including file with ID and version.
    Defining key with value.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_4.mal"
    ).test(
        defines=['id', 'version', 'key']
    )

def test_include_5() -> None:
    '''
    Including one file with ID and another with version.
    Defining key with value.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_5.mal"
    ).test(
        defines=['id', 'version', 'key']
    )

def test_include_6() -> None:
    '''
    Include same file twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_6.mal"
    ).test(    
        defines=['id', 'version']
    )

def test_include_7() -> None:
    '''
    Defining keys ID and version after include.
    '''
    AnalyzerTestWrapper(
        test_file="test_include_7.mal"
    ).test(    
        defines=['id', 'version']
    )

def test_include_8() -> None:
    '''
    Test if circular includes are noticed
    '''
    AnalyzerTestWrapper(
        test_file="test_include_8.mal"
    ).test(
        error=True
    )