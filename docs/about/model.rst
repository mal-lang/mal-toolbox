
Model
-----

With a MAL language (e.g. `coreLang <https://github.com/mal-lang/coreLang>`_) defined in a .mar or .mal-file,
a :class:`maltoolbox.model.Model` can be created either from a model instance file or empty.

Assets and associations
"""""""""""""""""""""""
A model consists of assets and associations.

- An asset is a python object of a class that was dynamically generated using the MAL language with
  :class:`maltoolbox.language.classes_factory.LanguageClassesFactory`.

- An association is a connection between two or more assets.

The MAL language defines which assets can have an association between each other and what the 'field names' between them are called.

Example:
`Application` is an asset type defined in the MAL Language coreLang. The association `AppExecution` is defined in coreLang. It can exist between `Application` and `Application` through field names
`hostApp` and `appExecutedApps`, this is defined in the MAL language coreLang but can look different in other MAL languages.

Load/create a model
"""""""""""""""""""

With the MAL GUI
''''''''''''''''

You can use the `MAL GUI <https://github.com/mal-lang/mal-gui/>`_ to create models.
This is a program that lets you drag and drop assets and associations given that you have a MAL language define already.
It will output model files.

In Python code
''''''''''''''

First, you have to load the MAL language:

.. code-block:: python

    from maltoolbox.language import LanguageGraph, LanguageClassesFactory

    # First load the language either from .mal or .mar
    # lang_graph = LanguageGraph.from_mar_archive(lang_file_path)
    lang_graph = LanguageGraph.from_mal_spec(lang_file_path)

    # Then create the lang_classes_factory
    lang_classes_factory = LanguageClassesFactory(lang_graph)

With existing model instance file
(`see example <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/common/simple_example_model.yml>`_):

.. code-block:: python

    from maltoolbox.model import Model

    # Load the model (i.e. the simple_example_model.json, can also be .yml/yaml)
    model_file_path = "example_model.yml"
    instance_model = Model.load_from_file(model_file_path, lang_classes_factory)

Without existing model instance file:

.. code-block:: python

    from maltoolbox.model import Model

    # Create an empty model
    instance_model = Model("Example Model", lang_classes_factory)

    # Create and add asset of type supported by the MAL language
    application_class = lang_classes_factory.get_asset_class('Application')
    asset1 = application_class(name="Application 1")
    asset2 = application_class(name="Application 2")
    instance_model.add_asset(asset1)
    instance_model.add_asset(asset2)

    # Create and add association
    app_execution_class = lang_classes_factory.get_association_class(
        'AppExecution_hostApp_appExecutedApps'
    )
    association = app_execution_class(hostApp=[asset1], appExecutedApps=[asset2])
    instance_model.add_association(association)

For more info on how to use MAL Toolbox,
`Read the tutorial docs <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/model-generators/model_generator.py>`_.
