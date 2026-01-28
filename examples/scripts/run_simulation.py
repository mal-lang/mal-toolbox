"""Run the script from this directory"""

from malsim import MalSimulator, run_simulation
from malsim.scenario import Scenario

# Assumption that this script is run from root directory of this repo
SCENARIO_FILE = "../resources/scenario.yml"

scenario = Scenario.load_from_file(SCENARIO_FILE)
mal_simulator = MalSimulator.from_scenario(scenario)
_ = run_simulation(mal_simulator, scenario.agents)
