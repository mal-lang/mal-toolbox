//! Port of `maltoolbox/attackgraph/node.py`.
//!
//! `full_name` and `to_dict` need to resolve the owning model asset's
//! name, which (per this port's convention of not storing a persistent
//! `Model` reference on `AttackGraph` - see `crate::graph` module docs)
//! requires a `&Model` passed in; see `AttackGraph::full_name_of` and
//! `AttackGraph::to_dict`.
//!
//! `additive_model_effects`/`subtractive_model_effects` are copied
//! straight through from the language-graph attack step at construction
//! time, exactly as the Python original does (`None` when empty, never
//! an empty list) - mal-toolbox itself never applies them to a `Model`;
//! they're exposed as plain data for a downstream consumer (e.g.
//! mal-simulator) to interpret.

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

/// `Some(effects)` when non-empty, else `None` - mirrors
/// `lg_attack_step.additive_model_effects if len(...) > 0 else None`.
pub fn non_empty(effects: Vec<LanguageGraphModelEffect>) -> Option<Vec<LanguageGraphModelEffect>> {
    if effects.is_empty() {
        None
    } else {
        Some(effects)
    }
}

impl AttackGraphNode {
    /// Fallback full name when no model asset is available to resolve a
    /// name from: `"{id}:{name}"`, mirroring the Python original's
    /// `full_name` fallback branch. Prefer `AttackGraph::full_name_of`
    /// when a model is available, since it also honors
    /// `full_name_override` and the model-asset-derived name.
    pub fn fallback_full_name(&self) -> String {
        format!("{}:{}", self.id, self.name)
    }
}
