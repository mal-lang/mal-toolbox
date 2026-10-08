//! Port of `maltoolbox/attackgraph/node.py`'s `AttackGraphNode`.
//!
//! `AttackGraph` does not keep a persistent `Model` reference, so
//! resolving a node's full name requires a `&Model` passed in; see
//! `AttackGraph::full_name_of` and `AttackGraph::to_dict`.
//!
//! `additive_model_effects`/`subtractive_model_effects` are plain data
//! copied through from the language graph; mal-toolbox itself never
//! applies them to a `Model` - a downstream consumer (e.g. mal-simulator)
//! interprets them.

use std::collections::HashMap;
use std::collections::HashSet;

use serde_json::{Map, Value};

use maltoolbox_language::graph::attack_step::{AttackStepType, CausalMode};
use maltoolbox_language::graph::model_effect::LanguageGraphModelEffect;

use crate::detector::Detector;
use crate::ids::AttackGraphNodeId;

#[derive(Debug, Clone)]
pub struct AttackGraphNode {
    pub id: i64,
    pub lg_attack_step: maltoolbox_language::graph::AttackStepId,
    pub name: String,
    pub step_type: AttackStepType,
    pub causal_mode: Option<CausalMode>,
    pub ttc: Option<Value>,
    pub tags: Vec<String>,
    pub additive_model_effects: Option<Vec<LanguageGraphModelEffect>>,
    pub subtractive_model_effects: Option<Vec<LanguageGraphModelEffect>>,
    pub model_asset: Option<i64>,
    pub existence_status: Option<bool>,
    pub children: HashSet<AttackGraphNodeId>,
    pub parents: HashSet<AttackGraphNodeId>,
    pub extras: Map<String, Value>,
    pub detectors: HashMap<String, Detector>,
    /// Explicitly-set full name, used when a node is loaded from a file
    /// without an accompanying model (see `attack_graph_from_dict`).
    pub full_name_override: Option<String>,
}

/// Returns `Some(effects)` when non-empty, else `None`.
pub fn non_empty(effects: Vec<LanguageGraphModelEffect>) -> Option<Vec<LanguageGraphModelEffect>> {
    if effects.is_empty() {
        None
    } else {
        Some(effects)
    }
}

impl AttackGraphNode {
    /// Fallback full name (`"{id}:{name}"`) used when no model asset is
    /// available to resolve a name from. Prefer `AttackGraph::full_name_of`
    /// when a model is available, since it also honors
    /// `full_name_override` and the model-asset-derived name.
    pub fn fallback_full_name(&self) -> String {
        format!("{}:{}", self.id, self.name)
    }
}
