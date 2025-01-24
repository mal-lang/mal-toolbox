from maltoolbox.translators.updater import load_model_from_older_version
from maltoolbox.language.classes_factory import LanguageClassesFactory
from maltoolbox.model import Model

def test_converts_from_0_1(corelang_lang_graph):
    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)

    old_model_file = 'tests/testdata/simple_example_model_0.1.8.yml'
    new_model_file = 'tests/testdata/simple_example_model.yml'

    old_model = load_model_from_older_version(
        old_model_file, lang_classes_factory,
    )

    new_model = Model.load_from_file(
        new_model_file, lang_classes_factory=lang_classes_factory,
    )

    assert old_model._to_dict() == new_model._to_dict()

def test_converts_from_0_0(corelang_lang_graph):
    """Load the older_version_example_model.json from testdata, and check if
    its version is correct"""

    lang_classes_factory = LanguageClassesFactory(corelang_lang_graph)

    old_model_file = 'tests/testdata/simple_example_model_0.0.38.json'
    new_model_file = 'tests/testdata/simple_example_model.yml'

    old_model = load_model_from_older_version(
        old_model_file, lang_classes_factory,
    )

    new_model = Model.load_from_file(
        new_model_file, lang_classes_factory=lang_classes_factory,
    )

    assert old_model._to_dict() == new_model._to_dict()
