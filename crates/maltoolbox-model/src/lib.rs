//! Port of mal-toolbox's `maltoolbox/model.py`: the instance model
//! (assets + associated-asset links) built against a compiled
//! [`maltoolbox_language::graph::LanguageGraph`].

pub mod file;
pub mod model;

pub use file::{from_dict, load_from_file, save_to_file, LoadError};
pub use model::{Model, ModelAsset, ModelError, MALTOOLBOX_VERSION};
