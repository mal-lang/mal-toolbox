from maltoolbox.language import LanguageGraph
from maltoolbox.model import Model
from maltoolbox.translators.updater import load_model_from_older_version


def _to_dict_ignoring_version(model: Model) -> dict:
    """Like `model._to_dict()`, but with `"MAL-Toolbox Version"` removed.

    Neither `simple_example_model_0.0.38.json` nor
    `simple_example_model_0.1.8.yml` ever recorded a version (the field
    predates them), so `load_model_from_older_version` picks up the
    "no version recorded" default - the live `maltoolbox.__version__` -
    which will never match `simple_example_model.yml`'s own explicitly
    recorded version. This comparison only ever passed before because of
    a separate, documented pure-Python bug where `to_dict()` ignored
    `self.maltoolbox_version` entirely and always wrote the live version
    on *both* sides regardless (see PORTING_NOTES.md §3); fixing that bug
    (an intentional, accepted divergence - see
    PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 status) means this field
    is no longer meaningful to compare here.
    """
    d = model._to_dict()
    d['metadata'].pop('MAL-Toolbox Version', None)
    return d


def test_converts_from_0_0(corelang_lang_graph: LanguageGraph):

    old_model_file = 'tests/testdata/simple_example_model_0.0.38.json'
    new_model_file = 'tests/testdata/simple_example_model.yml'

    converted_old_model = load_model_from_older_version(
        old_model_file, corelang_lang_graph
    )

    new_model = Model.load_from_file(new_model_file, corelang_lang_graph)

    assert _to_dict_ignoring_version(converted_old_model) == _to_dict_ignoring_version(new_model)


def test_converts_from_0_1(corelang_lang_graph: LanguageGraph):

    old_model_file = 'tests/testdata/simple_example_model_0.1.8.yml'
    new_model_file = 'tests/testdata/simple_example_model.yml'

    converted_old_model = load_model_from_older_version(
        old_model_file, corelang_lang_graph
    )

    new_model = Model.load_from_file(
        new_model_file,
        corelang_lang_graph,
    )

    assert _to_dict_ignoring_version(converted_old_model) == _to_dict_ignoring_version(new_model)


def test_converts_from_0_2(corelang_lang_graph: LanguageGraph):
    """Load the older_version_example_model.json from testdata, and check if
    its version is correct
    """
    old_model_file = 'tests/testdata/simple_example_model_0.2.0.yml'
    new_model_file = 'tests/testdata/simple_example_model.yml'

    converted_old_model = load_model_from_older_version(
        old_model_file, corelang_lang_graph
    )

    new_model = Model.load_from_file(
        new_model_file,
        corelang_lang_graph,
    )

    assert converted_old_model._to_dict() == new_model._to_dict()
