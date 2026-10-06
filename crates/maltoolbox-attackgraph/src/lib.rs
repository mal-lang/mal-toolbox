//! Port of mal-toolbox's `maltoolbox/attackgraph/` package: builds an
//! [`AttackGraph`] of concrete attack/defense steps from a [`Model`] and
//! its [`maltoolbox_language::graph::LanguageGraph`].
//!
//! Unlike the Python original, [`AttackGraph`] does not hold a
//! persistent reference to the [`Model`] it was built from - every
//! method that needs one (`to_dict`, regeneration, full-name resolution)
//! takes `&Model` as an explicit parameter instead. Python's
//! `self.model` works because the same mutable object is shared between
//! caller and graph; doing that in Rust would require wrapping `Model`
//! in `Rc<RefCell<_>>` just so external code can mutate it out from
//! under a struct that otherwise only reads it.

pub mod detector;
pub mod expr_follow;
pub mod factories;
pub mod generate;
pub mod graph;
pub mod ids;
pub mod node;
pub mod node_getters;
pub mod partially_generate;
pub mod ttcs;

pub use detector::Detector;
pub use factories::{create_attack_graph, FactoryError};
pub use graph::AttackGraph;
pub use ids::AttackGraphNodeId;
pub use node::AttackGraphNode;

#[derive(Debug, thiserror::Error)]
pub enum GraphError {
    #[error("{0}")]
    Malformed(String),
    #[error("{0}")]
    StepExpression(String),
    #[error("Node index {0} already in use.")]
    DuplicateNodeId(i64),
    #[error("{0}")]
    Language(#[from] maltoolbox_language::graph::GraphError),
    #[error("{0}")]
    Model(#[from] maltoolbox_model::ModelError),
    #[error("{0}")]
    FileUtil(#[from] maltoolbox_fileutil::FileUtilError),
}
