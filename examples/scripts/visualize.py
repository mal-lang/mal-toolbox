from maltoolbox.attackgraph import create_attack_graph
from maltoolbox.visualization.graphviz_utils import render_attack_graph, render_model

lang_file = "../resources/org.mal-lang.coreLang-1.0.0.mar" 
model_file = "../resources/model.yml"

# Generate attack graph from language + model
attack_graph = create_attack_graph(lang_file, model_file)

# Send model to graphviz
render_model(attack_graph.model)

# Send attack graph to graphviz
render_attack_graph(attack_graph)
