from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
File to test set operations (/\\ and \\/ and -)
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/operation_test_files"], indirect=True)

# TESTS FOR /\
def test_operation_1() -> None:
    '''
    Test /\\ correctly (used in variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_2() -> None:
    '''
    Test /\\ correctly (used directly in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_2.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_3() -> None:
    '''
    Test /\\ directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_3.mal",
        error_msg="Last step is not attack step"
    )

def test_operation_4() -> None:
    '''
    Test /\\ directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_4.mal",
        error_msg="Attack step 'foundWindows' not defined for asset 'OperatingSystem'"
    )

def test_operation_5() -> None:
    '''
    Test /\\ in variable but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_5.mal",
        error_msg="Types 'Windows' and 'Linux' have no common ancestor\n" + \
                  "Variable 'targets' defined at 7 does not point to an asset"
    )

def test_operation_6() -> None:
    '''
    Test /\\ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_6.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_7() -> None:
    '''
    Test /\\ directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_7.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )






# Tests for \/
def test_operation_8() -> None:
    '''
    Test \\/ correctly (used in variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_8.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_9() -> None:
    '''
    Test \\/ correctly (used directly in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_9.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_10() -> None:
    '''
    Test \\/ directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_10.mal",
        error_msg="Last step is not attack step"
    )

def test_operation_11() -> None:
    '''
    Test \\/ directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_11.mal",
        error_msg="Attack step 'foundWindows' not defined for asset 'OperatingSystem'"
    )

def test_operation_12() -> None:
    '''
    Test \\/ in variable but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_12.mal",
        error_msg="Types 'Windows' and 'Linux' have no common ancestor\n" + \
                  "Variable 'targets' defined at 7 does not point to an asset"
    )

def test_operation_13() -> None:
    '''
    Test \\/ directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_13.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_14() -> None:
    '''
    Test \\/ directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_14.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )





# TESTS FOR -
def test_operation_15() -> None:
    '''
    Test - correctly (used in variable)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_15.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_16() -> None:
    '''
    Test - correctly (used directly in step)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_16.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem']
    )

def test_operation_17() -> None:
    '''
    Test - directly in the step but do not point to a step (only point to asset)
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_17.mal",
        error_msg="Last step is not attack step"
    )

def test_operation_18() -> None:
    '''
    Test - directly in the step but do not use an attack step belonging to the LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_18.mal",
        error_msg="Attack step 'foundWindows' not defined for asset 'OperatingSystem'"
    )

def test_operation_19() -> None:
    '''
    Test - directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_19.mal",
        error_msg="Types 'Windows' and 'Linux' have no common ancestor\n" + \
                  "Variable 'targets' defined at 7 does not point to an asset"
    )

def test_operation_20() -> None:
    '''
    Test - directly in the step but use assets without an LCA
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_20.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Network', 'Machine', 'Computer', 'ThinkPad', 'Asus']
    )

def test_operation_21() -> None:
    '''
    Test - directly in the step using an attack step from the LCA's parent
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_21.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Computer', 'Windows', 'Linux', 'OperatingSystem', 'Software']
    )




# General functionality test
def test_operation_22() -> None:
    '''
    Test complex operation
    '''
    AnalyzerTestWrapper(
        test_file="test_operation_22.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Main','Generator','Grandparent','Parent','Child','Grandchild']
    )