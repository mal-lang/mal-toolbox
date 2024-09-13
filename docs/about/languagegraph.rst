LanguageGraph
-------------

The :class:`maltoolbox.language.languagegraph.LanguageGraph` contains a graph representation of the MAL language that is loaded.
`Read more about MAL <https://mal-lang.org/>`_.

It will also contain a language specification which is a dict containing the language (asset types, association types and attack steps).

Load an AttackGraph
"""""""""""""""""""

.. code-block:: python

    from maltoolbox.language import LanguageGraph

    # First load the language either from .mal or .mar
    # lang_graph = LanguageGraph.from_mar_archive(lang_file_path)
    lang_graph = LanguageGraph.from_mal_spec(lang_file_path)
