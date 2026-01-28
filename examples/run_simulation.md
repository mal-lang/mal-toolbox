# Run a simulation

Prerequisites:
- [MAL Simulator](https://github.com/mal-lang/mal-simulator)
- A MAL Language [Compiling a MAL Lanugage](compile_language.md).
- A model file (.yml/.json) - [Creating a MAL model](create_model.md).

## Option 1: Scenario file

A scenario contains the language file, the model file and agents.
A scenario can also contain rewards, observability, actionability, false positive/negative rates.

Refer to the README on how to create an up-to-date scenario file, but it will look something like this (yml):

```
lang_file: <.MAR | .MAL file path>
model_file: <.yml | .json file path>
agents:
    <agent_name>:
        type: 'attacker' | 'defender'
        agent_class: <AGENT CLASS>

        # below only for attacker
        entry_points: [<ATTACK STEP FULL NAME>]   # required
        goals: [<ATTACK STEP FULL NAME>]          # optional

rewards:
    per_asset_type:
        <ASSET TYPE>:
            <ATTACK STEP NAME>: float
    per_asset_name:
        <ASSET NAME>:
            <ATTACK STEP NAME>: float

# Format is the same for observable_steps, actionable_steps, false_positive_rates, false_negative_rates and all are optional.
```

The scenario file can be run with the MalSimulator cli: `malsim guides/scripts/scenario.yml` which also takes some optional args like seed and ttc mode.

It can also be run programatically like this:
```python

from malsim import MalSimulator, load_scenario, run_simulation

scenario = load_scenario(SCENARIO_PATH)
sim = MalSimulator.from_scenario(scenario)
run_simulation(sim, scenario.agents)

```

See [example script](scripts/run_simulation.py).

## Option 2: Scenario object

If you don't want to load a scenario file but create the scenario in memory, you can do it like this:

```python

from malsim import MalSimulator, run_simulation
from malsim.scenario import Scenario

scenario = Scenario(
    lang_file=LANG_FILE,
    model_file=MODEL_FILE,
    agents={
        'Attacker1': {
            'type': 'attacker',
            'agent_class': 'BreadthFirstAttacker',
            'entry_points': ['User:3:phishing', 'Host:0:connect']
        },
        'Defender1': {
            'type': 'defender',
            'agent_class': 'PassiveAgent'
        }
    }
)

sim = MalSimulator.from_scenario(scenario)
run_simulation(sim, scenario.agents)

```
