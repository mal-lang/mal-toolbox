from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `let` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/let_test_files"], indirect=True)

def test_let_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer','Platform','Software','Hardware'],
        lets=[('Computer', ['components'])]
    )

def test_let_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines two assets with name.
    Defines same let twice.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer','Platform','Hardware','Software'],
        lets=[('Computer', ['component'])]
    )

def test_let_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let not pointing to asset.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer'],
        lets=[('Computer', ['component'])]
    )

def test_let_4() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2', ['component','another_component'])]
    )


def test_let_5() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Redefines let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2',['component'])]
    )

def test_let_6() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let in circular manner.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_6.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset1', ['component1','component2'])]
    )

def test_let_7() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let when a parent has no association.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_7.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset3', ['component'])]
    )

def test_let_8() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let using a parents association.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_8.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset3', ['component'])]
    )

def test_let_9() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines let only in a parent.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_9.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset3', ['component'])]
    )
    
def test_let_10() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Redefines the exact same let in asset in a hierarchy.
    '''
    AnalyzerTestWrapper(
        test_file="test_let_10.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3','Asset4'],
        lets=[('Asset1', ['component']),('Asset2',['component'])]
    )