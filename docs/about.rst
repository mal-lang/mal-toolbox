About MAL Toolbox
==============

MAL Toolbox is a collection of tools related to MAL (Meta Attack Language).
It can be used to generate models and attackgraphs from MAL languages,
which can be used to run simulations or analysis.


LanguageGraph
-------------
The :class:`maltoolbox.language.languagegraph.LanguageGraph` will contain a graph representation of the MAL language that is loaded.
It will also contain a language specification which is a dict representing the language (possible asset types, associations and attack steps).

Model
-----
With a MAL language (e.g. `coreLang <https://github.com/mal-lang/coreLang>`_) defined in a .mar or .mal-file, a :class:`maltoolbox.model.Model` can be created
either from a model instance file or empty.

Assets and associations
""""""""""""""""""""""
A model consists of assets and associations.

- An asset is a python object which is dynamically generated using the MAL language with (:class:`maltoolbox.language.classes_factory.LanguageClassesFactory`).

- An association is a connection between two or more assets. The MAL language defines which assets can have an association between each other and what the 'field names' between them are called.

Example:
`Application` is an asset type defined in the MAL Language coreLang. It has certain attack steps attached defined in coreLang.
The association `AppExecution` is defined in coreLang. It can exist between `Application` and `Application` through field names
`hostApp` and `appExecutedApps`, this is defined in the MAL language coreLang but can look different in other MAL languages.

Generating a model
""""""""""""""""""

First, you have to load the MAL language:

.. code-block:: python

    from maltoolbox.language import LanguageGraph, LanguageClassesFactory

    # First load the language either from .mal or .mar
    # lang_graph = LanguageGraph.from_mar_archive(lang_file_path)
    lang_graph = LanguageGraph.from_mal_spec(lang_file_path)

    # Then create the lang_classes_factory
    lang_classes_factory = LanguageClassesFactory(lang_graph)

With existing model instance file (`see example <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/basics/simple_example_model.json>`_):

.. code-block:: python

    from maltoolbox.model import Model

    # Load the model (i.e. the simple_example_model.json, can also be .yml/yaml)
    instance_model = Model.load_from_file(model_file_path, lang_classes_factory)

Without existing model instance file:

.. code-block:: python

    from maltoolbox.model import Model

    # Create an empty model
    instance_model = Model("Example Model", lang_classes_factory)

    # Create and add asset of type supported by the MAL language
    asset = model.lang_classes_factory.ns.Application(name="Example Application")
    instance_model.add_asset(asset)

For more info on how to use MAL Toolbox, `Read the tutorial docs <https://github.com/mal-lang/mal-toolbox-tutorial/blob/main/res/mal-toolbox/model-generators/model_generator.py>`_.

AttackGraph
-----------

From a Model it is possible to create an :class:`maltoolbox.attackgraph.AttackGraph`.

While a Model consists of assets and associations, an AttackGraph instead contains :class:`maltoolbox.attackgraph.AttackGraphNode`.
The AttackGraphNode can be an attack or defense step (defined in the MAL language for each type of asset).

The point of the AttackGraph is to give an abstraction that shows each step an Attacker can take, and a way to analyze viable
paths for an attacker and run simulations.

Generating an AttackGraph
""""""""""""""""""""""""

If you already have an instance model file and .mal/.mar, the easiest way to create an AttackGraph is to use the wrapper :func:`maltoolbox.wrappers.create_attack_graph`
which combines all steps from model file to the AttackGraph:

.. code-block:: python
    
    from maltoolbox.wrappers import create_attack_graph

    attack_graph = create_attack_graph(lang_file, model_file)


To generate an AttackGraph from an already generated model:

.. code-block:: python
    
    from maltoolbox.attackgraph import AttackGraph

    attack_graph = AttackGraph(lang_graph, instance_model)

From AttackGraph file:

.. code-block:: python

    from maltoolbox.attackgraph import AttackGraph

    # Load the attack graph
    loaded_attack_graph = AttackGraph()
    loaded_attack_graph.load_from_file(example_graph_path)

Note: The `load_from_file` will most likely be a class method in the future.
