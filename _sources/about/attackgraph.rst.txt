AttackGraph
-----------

From a Model it is possible to create an :class:`maltoolbox.attackgraph.AttackGraph`.

The point of the AttackGraph is to give an abstraction that shows each step an attacker can take, analyze
paths for an attacker and run simulations.

While a Model consists of assets and associations, an AttackGraph instead contains :class:`maltoolbox.attackgraph.AttackGraphNode`.
The AttackGraphNode can be an attack or defense step (defined in the MAL language for each type of asset).

AttackGraphNode
""""""""""""""""
An AttackGraphNode is an attack step or a defense step, decided by its type.
If the node has type `and` or `or`, it is considered an attack step.

Nodes can have these properties:

* Viable
    - Determine if a node can be traversed under any circumstances or
    if the model structure or active defense steps makes it unviable.
* Necessary
    - Determine if a node is necessary for the attacker or if the
    model structure means it is not needed(it behaves as if it were already
    compromised) to compromise children attack steps.
* Compromised
    - An attacker compromises an attack step by reaching it (performing the attack step)
* Traversable
    -  Determines whether an attack step can be compromised in the next step.
* Reachable
    - Determines if a specific or any attacker can reach an attack step any time in the future from its currently reached attack steps.

Generating an AttackGraph
"""""""""""""""""""""""""

If you already have an instance model file and .mal/.mar, the easiest way to create an AttackGraph
is to use the wrapper :func:`maltoolbox.attackgraph.create_attack_graph`
which combines all steps from model file to the AttackGraph:

.. code-block:: python
    
    from maltoolbox.attackgraph import create_attack_graph

    lang_file = "org.mal-lang.coreLang-1.0.0.mar"
    model_file = "example-model.yml"
    attack_graph = create_attack_graph(lang_file, model_file)


To generate an AttackGraph from existing lang graph and model, use the init of
:func:`maltoolbox.attackgraph.attackgraph.AttackGraph`:

.. code-block:: python

    # Create the attack graph from existing LanguageGraph and Model
    attack_graph = AttackGraph(lang_graph, model)

From AttackGraph file :func:`maltoolbox.attackgraph.attackgraph.AttackGraph.load_from_file`:

.. code-block:: python

    from maltoolbox.attackgraph import AttackGraph

    # Load the attack graph
    example_graph_path = "attackgraph.yml"
    loaded_attack_graph = AttackGraph.load_from_file(example_graph_path)

Analyzers
"""""""""
 
:mod:`maltoolbox.attackgraph.analyzers` contains analyzers for the attackgraph used to calculate viability and necessity.


Pattern matching
""""""""""""""""
 
:mod:`maltoolbox.patternfinder.attack_graph_patterns` contains a regex-like feature to search for patterns in an attack graph.

Example:

.. code-block:: python

    attack_graph: AttackGraph

    # Create the search pattern to find paths from Node1 to any node
    pattern = SearchPattern(
        [
            SearchCondition(
                lambda node: node.name == "Node1"
            ),
            SearchCondition(
                SearchCondition.ANY
            ),
            SearchCondition(
                lambda node: node.name == "Node4"
            )
        ]
    )

    # Returns a list of node paths that match
    paths = pattern.find_matches(attack_graph)
