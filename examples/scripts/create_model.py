"""Run the script from this directory"""

from maltoolbox.model import Model
from maltoolbox.language import LanguageGraph

# You can load language from .mar archives (created with 'malc')
# or directly from .mal-files
file_path = "../resources/org.mal-lang.coreLang-1.0.0.mar"
corelang_graph = LanguageGraph.load_from_file(file_path)

# Create an empty model from the language
model = Model("Test Model", corelang_graph)

# Add two assets to the model using the asset type name
# defined in your MAL Language
app1 = model.add_asset(asset_type = 'Application', name = 'Application 1')
app2 = model.add_asset(asset_type = 'Application', name = 'Application 2')

# Create an association between app1 and app2 using the field name of
# the association which was defined in your MAL Language
app1.add_associated_assets(fieldname='appExecutedApps', assets={app2})

# Save your model for later use
model.save_to_file('model.yml')
