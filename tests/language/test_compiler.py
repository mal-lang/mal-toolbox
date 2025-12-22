from maltoolbox.language.compiler import MalCompiler
import pytest


def compile_lang(tmp_path, src: str):
    lang_file = tmp_path / "test.mal"
    lang_file.write_text(src)
    return MalCompiler().compile(str(lang_file))


@pytest.mark.parametrize(
    "asset_id",
    [
        "asset-name",     # hyphen
        "asset.name",     # dot
        "asset name",     # space
        "asset$",         # special char
    ],
)
def test_compiler_illegal_asset_names(tmp_path, asset_id):
    lang = f"""
    #id: "test-lang"
    #version: "0.0.0"

    category TestCategory {{
        asset {asset_id} {{
            | step1
        }}
    }}
    """
    with pytest.raises(Exception):
        compile_lang(tmp_path, lang)


def test_compiler_valid_asset_name_control(tmp_path):
    lang = """
    #id: "test-lang"
    #version: "0.0.0"

    category TestCategory {
        asset Valid_Asset {
            | step1
        }
    }
    """
    compile_lang(tmp_path, lang)


def test_compiler_non_existing_step(tmp_path):
    lang = """
    #id: "test-lang"
    #version: "0.0.0"

    category TestCategory {
        asset asset {
            | step1 -> nonExistingStep
        }
    }
    """
    with pytest.raises(Exception):
        compile_lang(tmp_path, lang)
