from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `modeler info` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/modeler_info_test_files"], indirect=True)

def test_modeler_info_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines modeler info.
    '''
    AnalyzerTestWrapper(
        test_file="test_modeler_info_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_modeler_info_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines modeler info twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_modeler_info_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )