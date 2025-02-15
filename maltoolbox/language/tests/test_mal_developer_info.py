from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `developer info` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/developer_info_test_files"], indirect=True)

def test_developer_info_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines developer info.
    '''
    AnalyzerTestWrapper(
        test_file="test_developer_info_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_developer_info_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines developer info twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_developer_info_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )