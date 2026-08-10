from pathlib import Path

import pytest

from maltoolbox.language import LanguageGraph
from maltoolbox.language.compiler import MalCompiler
from maltoolbox.language.compiler.lang import PARSER


def format_ast(lang_file: Path) -> str:
    """Return a pretty-printed tree-sitter AST for a .mal file"""
    tree = PARSER.parse(lang_file.read_bytes())

    lines = []

    def visit(node, depth):
        prefix = "  " * depth
        if node.child_count == 0:
            lines.append(f"{prefix}{node.type} {node.text!r}")
        else:
            lines.append(f"{prefix}{node.type}")
        for child in node.children:
            visit(child, depth + 1)

    visit(tree.root_node, 0)
    return "\n".join(lines)


def compile_lang(tmp_path, src: str):
    lang_file = tmp_path / 'test.mal'
    lang_file.write_text(src)
    return MalCompiler().compile(str(lang_file))


@pytest.mark.parametrize(
    'asset_id',
    [
        'asset-name',  # hyphen
        'asset.name',  # dot
        'asset name',  # space
        'asset$',  # special char
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
    with pytest.raises(Exception):  # noqa: B017
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
    with pytest.raises(Exception):  # noqa: B017
        compile_lang(tmp_path, lang)


def test_compile_actions_effects():
    """Test that we can pickle and unpickle a language graph attack step"""
    lang_graph = LanguageGraph.load_from_file('tests/testdata/actions_effects_lang.mal')
    assert lang_graph.assets['AssetA'].attack_steps['attack'].causal_mode == 'action'
    assert lang_graph.assets['AssetB'].attack_steps['hack'].causal_mode == 'effect'
    assert lang_graph.assets['AssetB'].attack_steps['attack'].causal_mode == 'action'
    assert lang_graph.assets['AssetB'].attack_steps['test'].causal_mode is None

def test_compile_wiperlang():
    """Test that we can compile the wiperlang.mal language"""
    result = MalCompiler().compile("tests/testdata/wiperLang.mal")

    try:
        malware_asset = next(asset for asset in result["assets"] if asset["name"] == "Malware")
    except StopIteration:
        pytest.fail("Malware asset not found")
    try:
        activate_step = next(step for step in malware_asset["attackSteps"] if step["name"] == "activate")
    except StopIteration:
        pytest.fail("activate attack step not found in Device asset")
    assert activate_step["reaches"]["stepExpressions"][0]["name"] == "trigger"

    try:
        device_asset = next(asset for asset in result["assets"] if asset["name"] == "Device")
    except StopIteration:
        pytest.fail("Device asset not found")
    try:
        infect_step = next(step for step in device_asset["attackSteps"] if step["name"] == "infect")
    except StopIteration:
        pytest.fail("infect attack step not found in Device asset")

    assert infect_step["reaches"]["stepExpressions"][0]["lhs"]["name"] == "malware"
    assert infect_step["reaches"]["stepExpressions"][0]["rhs"]["name"] == "activate"
    
    assert infect_step["append_reaches"]["stepExpressions"][0]["base"]["name"] == "self"
    assert infect_step["append_reaches"]["stepExpressions"][0]["targets"][0]["stepExpression"]["name"] == "malware"
    assert infect_step["append_reaches"]["stepExpressions"][0]["targets"][0]["subType"] == "Wiper"
    
    wiper_lang = LanguageGraph(result)

    device = wiper_lang.assets["Device"]
    wiper = wiper_lang.assets["Wiper"]
    assert wiper.attack_steps["exfiltrate"] in wiper.attack_steps["activate"].own_children
    assert wiper.attack_steps["propagate"] in wiper.attack_steps["activate"].own_children
    assert wiper.super_assets[1].attack_steps["trigger"] in wiper.super_assets[1].attack_steps["activate"].own_children
    assert device.attack_steps["infect"] in wiper.super_assets[1].attack_steps["activate"].own_parents

    device_infect = device.attack_steps["infect"]
    assert device_infect.own_additive_model_effects[0].base[0].field_name == "self", "Device:infect A> base should be self"
    assert not device_infect.own_additive_model_effects[0].targets[0].assoc_op, "Device:infect A> target should not be assoc_op"
    assert device_infect.own_additive_model_effects[0].targets[0].assoc_traversal[0].field_name == "malware"
    assert device_infect.own_additive_model_effects[0].targets[0].assoc_traversal[0].asset_filter == wiper_lang.assets["Wiper"]

    wiper_exfiltrate = wiper.attack_steps["exfiltrate"]
    assert wiper_exfiltrate.own_additive_model_effects[0].base[0].field_name == "victim" 
    assert wiper_exfiltrate.own_additive_model_effects[0].base[1].field_name == "data"
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_op
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_traversal[0].field_name == "victim"
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_traversal[1].field_name == "inet"
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_traversal[2].field_name == "hosts"
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_traversal[2].asset_filter == wiper_lang.assets["C2Server"]
    assert wiper_exfiltrate.own_additive_model_effects[0].targets[0].assoc_traversal[3].field_name == "data"

def test_compile_basic_dynamal_languages():
    dynamal_test_langs_dir = Path("tests/testdata/dynamal_test_langs/basic")
    for lang_file in dynamal_test_langs_dir.glob("*.mal"):
        LanguageGraph.from_mal_spec(lang_file)

def test_compile_intermediate_dynamal_languages():
    dynamal_test_langs_dir = Path("tests/testdata/dynamal_test_langs/intermediate")
    for lang_file in dynamal_test_langs_dir.glob("*.mal"):
        LanguageGraph.from_mal_spec(lang_file)

def test_compile_advanced_dynamal_languages():
    dynamal_test_langs_dir = Path("tests/testdata/dynamal_test_langs/advanced")
    for lang_file in dynamal_test_langs_dir.glob("*.mal"):
        LanguageGraph.from_mal_spec(lang_file)