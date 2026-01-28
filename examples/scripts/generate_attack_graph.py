from maltoolbox.attackgraph import create_attack_graph

# The .mar archive created with `malc`
lang_file = "../resources/org.mal-lang.coreLang-1.0.0.mar" 

# The model file created by maltoolbox
model_file = "../resources/model.yml"

# Generate attack graph from language + model
attack_graph = create_attack_graph(lang_file, model_file)

# Save your attack graph for later use
attack_graph.save_to_file('attack_graph.yml')
