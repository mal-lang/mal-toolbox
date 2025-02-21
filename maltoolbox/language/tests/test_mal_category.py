from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `category` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/category_test_files"], indirect=True)

def test_category_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    '''
    AnalyzerTestWrapper(
        test_file="test_category_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['Test']
    )

def test_category_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with same name twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_category_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['Test']
    )