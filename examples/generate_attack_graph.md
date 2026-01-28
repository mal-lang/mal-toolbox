# Generating an AttackGraph

Prerequisites:
- [MAL Toolbox](https://github.com/mal-lang/mal-toolbox)
- A compiled MAL Language [Compiling a MAL Lanugage](compile_language.md) or a .mal-file.
- A model file (.yml/.json) - [Creating a MAL model](create_model.md).

## Option 1: Using the MAL Toolbox cli

`maltoolbox attack-graph generate [options] <model_file> <lang_file>`

### Example:
```bash

# Language given as a .mal
maltoolbox attack-graph generate [options] model.yml main.mal

# Language given as a .mar
maltoolbox attack-graph generate [options] model.yml org.mal-lang.coreLang-1.0.0.mar

```

This will output the attack-graph (.yml) to the logging directory of mal-toolbox.

The default logging directory is './logs' in the directory where the maltoolbox command is run.

## Option 2: Generating an attack graph programatically

Use `maltoolbox.attackgraph.create_attack_graph`

See [example script](scripts/generate_attack_graph.py).