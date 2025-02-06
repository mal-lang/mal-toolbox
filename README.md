# MAL Toolbox overview

MAL Toolbox is a collection of python modules to help developers create and work with
MAL ([Meta Attack Language](https://mal-lang.org/)) models and attack graphs.

Attack graphs can be used to run simulations (see MAL Simulator) or analysis.
MAL Toolbox also gives the ability to view the AttackGraph/Model graphically in neo4j.

[Documentation](https://mal-lang.org/mal-toolbox/index.html)(Work in progress)

## The Language Module

The language module provides various tools to process MAL languages.

### The Language Specification Submodule

The language specification submodule provides functions to load the
specification from a .mar archive(`load_language_specification_from_mar`) or a
JSON file(`load_language_specification_from_json`). This specification will
then be used to generate python classes representing the assets and
associations of the language and to determine the attack steps for each asset
when generating the attack graph.

## The Model Module

With a MAL language a Model (a MAL instance model) can be created either
from a model file or empty.

The model class will store all of the relevant information to the MAL
instance model, most importantly the assets and associations that make it up.

Assets and associations are objects of classes created using the language
classes factory submodule in runtime. It also allows for `Attacker` objects
to be created and associated with attack steps on assets in the model.
The most relevant methods of the Model are the ones used to add different
elements to the model, `add_asset`, `add_association`, and `add_attacker`.

Model objects can be used to generate attack graphs with the AttackGraph module.

## The Attack Graph Module

The attack graph module contains tools used to generate attack graphs from
existing MAL instance models and analyse MAL attack graphs. The function used
to generate the attack graph is `generate_graph` and it requires the instance
model and language specification. The resulting attack graph will contain
nodes for each of the attack steps. The structure of the attack node data
class can be seen in `attackgraph/node.py` file. Of note are the lists of
children and parents which allow for easy reference to the other attack step
nodes related and the asset field which will contain the object in the model
instance to which this attack step belongs to, if this information is
available.

If it is relevant the `attach_attackers` function can be called on the
resulting attack graph with the instance model given as a parameter in order
to create attack step nodes that represent the entry points of the attackers
and attach them to the attack steps specified in the instance model.

## Ingestors Module

The ingestors module contains various tools that can make use of the instance
model or attack graph. Currently the Neo4J ingestor is the only one available
and it can be used to visualise the instance model and the attack graph.


# Usage

## Installation

```
pip install mal-toolbox
```

## Configuration
A default configuration file `default.conf` can be found in the package
directory. This contains the default values to use for logging and can also be
used to store the information needed to access the local Neo4J instance.

## Command Line Client
In addition to the modules that make up the MAL-Toolbox package it also
provides a simple command line client that can be used to easily generate
attack graphs from a .mar language specification file and a JSON instance
model file.

The usage is: `maltoolbox gen_ag [--neo4j] <model_json_file>
<language_mar_file>`

If the `--neo4j` flag is specified the model and attack graph will be loaded
into a local Neo4J instance.

## Code examples / Tutorial

To find code examples and tutorials, visit the
[MAL Toolbox Tutorial](https://github.com/mal-lang/mal-toolbox-tutorial/tree/main) repository.

# Tests
There are unit tests inside of ./tests.
Before running the tests, make sure to install the requirements in ./tests/requirements.txt with `python -m pip install -r ./tests/requirements.txt`.

To run all tests, use the `pytest` command. To run just a specific file or test function use `pytest tests/<filename>` or `pytest -k <function_name>`.
