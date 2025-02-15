from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest
import os

'''
A file to test different cases of the `abstract` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/abstract_asset_test_files"], indirect=True)

# TODO: is this test really needed? Doesn't the grammar prevent this kind of situation?
def test_abstract_assets_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines abstract asset without name.
    '''
    AnalyzerTestWrapper(
        test_file="test_abstract_asset_1.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System']
    )

def test_abstract_assets_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines abstract asset with name.
    Extends asset with abstract asset.
    '''
    AnalyzerTestWrapper(
        test_file="test_abstract_asset_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo', 'Bar']
    )

def test_abstract_assets_3() -> None:
    '''
    Test if chain of abstract extentions works
    '''
    AnalyzerTestWrapper(
        test_file="test_abstract_asset_3.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo','Bar','Baz']
    )

def test_abstract_assets_4() -> None:
    '''
    Abstract asset is never extended
    '''
    AnalyzerTestWrapper(
        test_file="test_abstract_asset_4.mal"
    ).test(
        warn=True,
        defines=['id','version'],
        categories=['System'],
        assets=['Foo','Bar']
    )