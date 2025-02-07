
Model
-----

With a MAL language (e.g. `coreLang <https://github.com/mal-lang/coreLang>`_) defined in a .mar or .mal-file,
a :class:`maltoolbox.model.Model` can be created either from a model instance file or empty.

Assets and associations
"""""""""""""""""""""""
A model consists of assets and associations.

- An asset is an instance of an asset type (LanguageGraphAsset)

- An association is a relation between two or more assets (an instance of a LanugageGraphAssociation)

The MAL language defines which assets can have an association between each other and what the 'field names' between them are called.

Example:
`Application` is an asset type defined in the MAL Language coreLang. The association `AppExecution` is defined in coreLang.
It can exist between `Application` and `Application` through field names `hostApp` and `appExecutedApps`,
this is defined in the MAL language coreLang but can look different in other MAL languages.

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

    from maltoolbox.language import LanguageGraph

    # First load the language either from .mal / .mar / .yml / .json
    lang_graph = LanguageGraph.load_from_file(lang_file_path)

With existing model instance file
(`see example <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/common/simple_example_model.yml>`_):

.. code-block:: python

    from maltoolbox.model import Model

    # Load the model (i.e. the simple_example_model.json, can also be .yml/yaml)
    model_file_path = "example_model.yml"
    instance_model = Model.load_from_file(model_file_path, lang_graph)

Without existing model instance file:

.. code-block:: python

    from maltoolbox.model import Model

    # Create an empty model
    instance_model = Model("Example Model", lang_graph)

    # Create and add assets of type supported by the MAL language
    asset1 = instance_model.add_asset('Application', 'Application1')
    asset2 = instance_model.add_asset('Application', 'Application2')

    # Create association between the assets
    asset1.add_associated_assets('appExecutedApps', asset2)

For more info on how to use MAL Toolbox,
`Read the tutorial docs <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/model-generators/model_generator.py>`_.
