from conftest import path_testdata
from maltoolbox.language import LanguageGraph

def test_corelang_with_union_different_assets_same_super_asset():
    """Uses edited coreLang language specification.
    An attackstep in IAMObject will contain a union between
    Identity and Group, which should be allowed, since they
    share the same super asset.
    """

    mar_file_path = path_testdata("corelang-union-common-ancestor.mar")

    # Make sure that it can generate
    LanguageGraph.from_mar_archive(mar_file_path)
