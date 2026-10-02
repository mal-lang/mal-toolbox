//! Port of `maltoolbox/language/language_graph_asset.py`.
//!
//! Unlike the Python dataclass, graph-traversal helpers that need to walk
//! `own_super_asset`/`own_sub_assets` (is_subasset_of, sub_assets,
//! super_assets, associations, variables, associations_to,
//! get_all_common_superassets) live as `LanguageGraph` methods in
//! `graph::mod` instead of on this struct, since in the arena/id design
//! they need access to the asset arena, not just `&self`.

use std::collections::HashMap;
use std::rc::Rc;

use serde_json::json;

use super::assoc::LanguageGraphAssociation;
use super::expr_chain::ExpressionsChain;
use super::ids::{AssetId, AttackStepId};
use super::{GraphError, LanguageGraph};

#[derive(Debug, Clone)]
pub struct LanguageGraphAsset {
    pub name: String,
    pub own_associations: HashMap<String, Rc<LanguageGraphAssociation>>,
    /// Both directly-defined and inherited attack steps, by name - mirrors
    /// the Python `attack_steps` dict, which `_inherit_attack_steps` also
    /// populates with synthesized inherited entries.
    pub attack_steps: HashMap<String, AttackStepId>,
    pub info: HashMap<String, String>,
    pub own_super_asset: Option<AssetId>,
    pub own_sub_assets: Vec<AssetId>,
    pub own_variables: HashMap<String, (AssetId, Option<ExpressionsChain>)>,
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
