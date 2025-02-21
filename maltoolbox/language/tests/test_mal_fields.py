from .mal_analyzer_test_wrapper import AnalyzerTestWrapper

from pathlib import Path
import pytest

'''
A file to test fields in MAL
'''

@pytest.mark.usefixtures("setup_test_environment")
@pytest.mark.parametrize("setup_test_environment", [Path(__file__).parent / "fixtures/fields_test_files"], indirect=True)

def test_fields_1() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines associations correctly
    '''
    AnalyzerTestWrapper(
        test_file="test_fields_1.mal"
    ).test(
        defines=['id', 'version'],
        categories=['System'],
        assets=['Asset1','Asset2','Asset3'],
        associations=[('Asset1',['a3']), ('Asset2',['a3','a3_again']), ('Asset3',['a1','a2'])]
    )
    
def test_fields_2() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines association in child with same name as parent
    '''
    AnalyzerTestWrapper(
        test_file="test_fields_2.mal",
        error_msg="Field Asset2.a3 previously defined at 10"
    )

def test_fields_3() -> None:
    '''
    Defines correct version and ID.
    Defines category with name.
    Defines association with same name as attack step
    '''
    AnalyzerTestWrapper(
        test_file="test_fields_3.mal",
        error_msg = "Field attack previously defined as an attack step at 7"
    )
