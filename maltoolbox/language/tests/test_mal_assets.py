from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest
import os

'''
A file to test different cases of the `asset` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/asset_test_files"], indirect=True)

def test_assets_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset without name.
    '''
    AnalyzerTestWrapper(
    test_file= "test_assets_1.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System']
    )

def test_assets_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper(
        test_file="test_assets_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_assets_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_assets_4.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_assets_5() -> None:
    '''
    Defines same asset in different categories
    '''
    AnalyzerTestWrapper(
        test_file="test_assets_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System', 'AnotherSystem'],
        assets=['Test']
    )

def test_assets_6() -> None:
    '''
    Defines assets correctly in different files
    '''

    AnalyzerTestWrapper(
        test_file="test_assets_6.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Test','AnotherTest'],
    )

def test_assets_7() -> None:
    '''
    Defines same asset in different files in different categories
    '''

    AnalyzerTestWrapper(
        test_file="test_assets_7.mal"
    ).test(
        error= True,
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Test'],
    )

def test_assets_8() -> None:
    '''
    Defines same asset in different files in same category
    '''
    AnalyzerTestWrapper(
        test_file="test_assets_8.mal"
    ).test(
        error= True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test'],
    )
