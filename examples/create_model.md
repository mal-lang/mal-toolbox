# Create a MAL Model

## Prerequisites:
- You have [mal-toolbox](https://github.com/mal-lang/mal-toolbox) installed.
- You have a language [compiled](compile_language.md) with `malc` or a .mal file.

## Creating a MAL Model using the mal-gui

1. Install [mal-gui](https://github.com/mal-lang/mal-gui/).
2. Launch mal-gui using the command `malgui` from command line and select your language.
3. Drag and drop the assets you want and create associations between them by SHIFT+Left clicking and dragging from one asset to another.
4. Export the model to either .yml or .json (you can export scenario files as well, this is for the `mal-simulator`)


## Create a MAL Model programatically using the mal-toolbox package

1. Load your language using maltoolbox.language.LanguageGraph.
2. Use the maltoolbox.model.Model class to create a model and add assets.
3. Add associations to your assets using `asset.add_associated_assets`.

See [example script](scripts/create_model.py).
