from maltoolbox.translators import model_to_gexf
from maltoolbox.translators.gexf import save_gexf_to_file
from maltoolbox.model import Model
from maltoolbox.language import LanguageGraph
import argparse
from gexfpy import Gexf, stringify


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a model to GEXF format")
    parser.add_argument(
        "model_file", type=str, help="Path to the model file (JSON or YAML)"
    )
    parser.add_argument(
        "lang_file", type=str, help="Path to the language file (MAL or MAR)"
    )
    parser.add_argument(
        "output_file", type=str, help="Path to the output GEXF file"
    )

    args = parser.parse_args()

    # Load the model and language graph
    lang_graph = LanguageGraph.load_from_file(filename=args.lang_file)
    model = Model.load_from_file(filename=args.model_file, lang_graph=lang_graph)

    # Convert the model to GEXF
    gexf: Gexf = model_to_gexf(model)

    save_gexf_to_file(gexf, args.output_file)