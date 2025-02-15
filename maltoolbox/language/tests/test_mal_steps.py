from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest
import os

'''
A file to test different if steps respect the hierarchy of the assets, namely when using '+>'
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/steps_test_files"], indirect=True)

def test_steps_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_1.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Test']
    )

def test_steps_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines a step with '+>' when there isn't parent asset with that step
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_2.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux']
    )

def test_steps_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Defines a step with '+>' when there is another asset with that step but it isn't extended
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_3.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_4() -> None:
    '''
    Define two assets which do not extend a parent and have steps without '+>'
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_4.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_5() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (&)
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_5.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_6() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (|)
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_6.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_7() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (E)
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_7.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'ThinkPad','Camera']
    )

def test_steps_8() -> None:
    '''
    Define an asset with a step inherited from the parent but with different types (!E)
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_8.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'ThinkPad','Camera']
    )

def test_steps_9() -> None:
    '''
    Test '+>' in a longer hierarchy
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_9.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_10() -> None:
    '''
    Test wrong type of extend step in a longer hierarchy
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_10.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_11() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines asset with name.
    Tests if two steps with the same names in different assets with different types does not throw error
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_11.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'OperatingSystem']
    )

def test_steps_12() -> None:
    '''
    Test if '+>' works if the extended asset is in another file
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_12.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_13() -> None:
    '''
    Test if mismatched step types works if the extended asset is in another file
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_13.mal"
    ).test(
        error=True,
        defines=['id', 'version'],
        categories=['System'],
        assets=['Machine', 'Computer','Thinkpad']
    )

def test_steps_14() -> None:
    '''
    Test inherit parent steps
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_14.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1', 'Asset2', 'Asset3', 'Asset4'],
        steps = [('Asset1',['step1']), ('Asset2',['step1','step2']), (
            'Asset3', ['step1','step2','step3']), ('Asset4',['step1','step2','step3','step4'])]
    )

def test_steps_15() -> None:
    '''
    A complex example which should work
    '''
    AnalyzerTestWrapper(
        test_file="test_steps_15.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Linux', 'Camera']
    )