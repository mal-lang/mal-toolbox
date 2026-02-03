# Visualize a MAL Model or Attack Graph

## Prerequisites:
- Create / find a MAL model file (.yml / .json)
- Compile / download a MAL langage: either a .mar or a .mal-file.

## Option 1: Visualize Model in Mal GUI

Install and use [mal gui](https://github.com/mal-lang/mal-gui) to load your model file (.yml or .json).


## Option 2: Visualize Model + Attack Graph with maltoolbox CLI

The MAL-toolbox cli supports visualizing an attack graph in `graphviz` when it is generated through the CLI.

`maltoolbox attack-graph generate <model_file> <lang_file> --graphviz`


## Option 3: Visualize Model + Attack Graph programatically

See [example script](scripts/visualize.py).
