LanguageGraph
-------------

The :class:`maltoolbox.language.languagegraph.LanguageGraph` contains a graph representation of the MAL language that is loaded.
`Read more about MAL <https://mal-lang.org/>`_.

It will also contain a language specification which is a dict containing the language (asset types, association types and attack steps).

Load a LanguageGraph
""""""""""""""""""""

.. code-block:: python

    from maltoolbox.language import LanguageGraph

    # Will load the MAL language (.mal/.mar) or a saved language graph (yml/json)
    lang_graph = LanguageGraph.load_from_file(lang_file_path)
