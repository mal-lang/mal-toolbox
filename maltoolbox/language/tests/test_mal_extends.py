from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

import os
import pytest
from pathlib import Path

'''
A file to test different cases of the `extends` instruction in MAL.
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/extend_test_files"], indirect=True)

def test_extends_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines asset with extends.
    '''
    AnalyzerTestWrapper(
        test_file="test_extends_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['OperatingSystem', 'Linux']
    )

def test_extends_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Extends asset with undefined asset.
    '''
    AnalyzerTestWrapper(
        test_file="test_extends_2.mal",
        error_msg = "Asset \'Foo2\' not defined"
    )

def test_extends_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Tests circular dependency with extends
    '''
    AnalyzerTestWrapper(
        test_file="test_extends_3.mal",
        error_msg = "Asset 'Foo1' extends in loop 'Foo1 -> Foo2 -> Foo3 -> Foo4 -> Foo5 -> Foo1'"
    )

def test_extends_4() -> None:
    '''
    Tests valid extends across files
    '''
    AnalyzerTestWrapper(
        test_file="test_extends_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test','SubTest'],
    )
