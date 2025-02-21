from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test different cases of the `info` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/info_test_files"], indirect=True)

def test_asset_info_1() -> None:
    '''
    Defines asset with name.
    Defines random info. (this should be allowed as to not break previous custom metas)
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_2() -> None:
    '''
    Defines asset with name.
    Defines random info twice.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_2.mal",
      error_msg = "Metadata random previously defined at 6"
    )

def test_asset_info_3() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step twice.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_3.mal",
      error_msg = "Metadata random previously defined at 9"
    )

def test_asset_info_4() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_5() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_5.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_6() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category twice.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_6.mal",
      error_msg = "Metadata random previously defined at 5"
    )

def test_asset_info_7() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_7.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_8() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step and category for two different categories.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_8.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_9() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and association
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_9.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_10() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and twice in the association
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_10.mal",
      error_msg = "Metadata random previously defined at 28"
    )

def test_asset_info_11() -> None:
    '''
    Defines asset with name.
    Defines random info in asset, attack step, category and association
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_11.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System','AnotherSystem'],
        assets=['Foo','Bar']
    )

def test_asset_info_12() -> None:
    '''
    Defines asset with name.
    Defines random info in two assets in the same category.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_12.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo','Bar']
    )


def test_asset_info_13() -> None:
    '''
    Defines asset with name.
    Defines random info in asset twice but with a different meta between them
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_13.mal",
      error_msg = "Metadata random previously defined at 5"
    )

def test_asset_info_14() -> None:
    '''
    Defines asset with name.
    Defines random info in asset and attack step.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_14.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )

def test_asset_info_15() -> None:
    '''
    Defines asset with name.
    Defines random info in two steps in the same asset.
    '''
    AnalyzerTestWrapper(
      test_file="test_asset_info_15.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Foo']
    )
