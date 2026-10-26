//! Core MAL language support: parsing `.mal` specs into a `LanguageGraph`.

pub mod compiler;
pub mod graph;
pub mod parser;

pub use compiler::{compile_file, CompileError};
pub use graph::file::{
    from_mal_spec, from_mar_archive, language_graph_from_dict,
    load_from_file as load_language_graph_from_file, save_to_file as save_language_graph_to_file,
    to_mar_archive as save_language_graph_to_mar_archive, LoadError as LanguageLoadError,
};
pub use graph::{generate_graph, language_graph_to_dict, GraphError, LanguageGraph};
pub use parser::new_parser;
