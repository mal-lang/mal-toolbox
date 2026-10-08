//! Port of `maltoolbox/language/language_graph_asset.py`.
//!
//! Traversal helpers that walk `own_super_asset`/`own_sub_assets`
//! (`is_subasset_of`, `sub_assets`, `super_assets`, `associations`,
//! `variables`, `associations_to`, `get_all_common_superassets`) live as
//! `LanguageGraph` methods in `graph::mod` rather than on this struct,
//! since the arena/id design needs access to the asset arena, not just
//! `&self`.

use std::collections::HashMap;
use std::rc::Rc;

use indexmap::IndexMap;
use serde_json::json;

use super::assoc::LanguageGraphAssociation;
use super::expr_chain::ExpressionsChain;
use super::ids::{AssetId, AttackStepId};
use super::{GraphError, LanguageGraph};

#[derive(Debug, Clone)]
pub struct LanguageGraphAsset {
    pub name: String,
    /// Insertion order must match the MAL spec's declaration order (as
    /// Python's `dict` preserves it) since it feeds attack-graph node
    /// creation order; `IndexMap` keeps this deterministic where a
    /// `HashMap` would not.
    pub own_associations: IndexMap<String, Rc<LanguageGraphAssociation>>,
    /// Both directly-defined and inherited attack steps, by name.
    /// Iteration order feeds attack-graph node id assignment
    /// (`generate.rs`'s `create_nodes_for`), so this must stay an
    /// `IndexMap`.
    pub attack_steps: IndexMap<String, AttackStepId>,
    pub info: HashMap<String, String>,
    pub own_super_asset: Option<AssetId>,
    pub own_sub_assets: Vec<AssetId>,
    pub own_variables: IndexMap<String, (AssetId, Option<ExpressionsChain>)>,
    pub is_abstract: bool,
}

impl LanguageGraphAsset {
    pub fn to_dict(&self, graph: &LanguageGraph) -> Result<serde_json::Value, GraphError> {
        let mut associations = serde_json::Map::new();
        for (k, v) in &self.own_associations {
            associations.insert(k.clone(), v.to_dict(graph));
        }

        let mut attack_steps = serde_json::Map::new();
        for step_id in self.attack_steps.values() {
            let step = graph.step(*step_id);
            attack_steps.insert(step.name.clone(), step.to_dict(graph)?);
        }

        let mut variables = serde_json::Map::new();
        for (name, (asset_id, expr)) in &self.own_variables {
            let expr_dict = match expr {
                Some(e) => e.to_dict(graph)?,
                None => serde_json::Value::Null,
            };
            variables.insert(
                name.clone(),
                json!([graph.asset(*asset_id).name.clone(), expr_dict]),
            );
        }

        Ok(json!({
            "name": self.name,
            "associations": associations,
            "attack_steps": attack_steps,
            "info": self.info,
            "super_asset": self.own_super_asset.map(|id| graph.asset(id).name.clone()).unwrap_or_default(),
            "sub_assets": self.own_sub_assets.iter().map(|id| graph.asset(*id).name.clone()).collect::<Vec<_>>(),
            "variables": variables,
            "is_abstract": self.is_abstract,
        }))
    }
}
