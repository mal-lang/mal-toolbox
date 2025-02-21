from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `association` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/association_test_files"], indirect=True)

def test_association_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines two asset with name.
    Defines an association between the assets.
    '''
    AnalyzerTestWrapper(
        test_file="test_association_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1', 'Asset2']
    )

def test_association_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines one asset with name.
    Defines an association between the asset 
    and one undefined right asset.
    '''
    AnalyzerTestWrapper(
        test_file="test_association_2.mal",
        error_msg="Right asset 'Asset1' is not defined"
    )

def test_association_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines one asset with name.
    Defines an association between the asset 
    and one undefined left asset.
    '''
    AnalyzerTestWrapper(
        test_file="test_association_3.mal",
        error_msg="Left asset 'Asset1' is not defined"
    )

def test_association_4() -> None:
    '''
    Creates an association correctly and tries to access an attack step via association
    '''
    AnalyzerTestWrapper(
        test_file="test_association_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['Example'],
        assets=['Asset1', 'Asset2']
    )

def test_association_5() -> None:
    '''
    Creates an association correctly and tries to access an attack step via association which is not defined
    '''
    AnalyzerTestWrapper(
        test_file="test_association_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['Example'],
        assets=['Asset1', 'Asset2']
    )

def test_association_6() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines an association between undefined assets.
    '''
    AnalyzerTestWrapper(
        test_file="test_association_6.mal",
        error_msg="Left asset 'Asset1' is not defined"
    )
