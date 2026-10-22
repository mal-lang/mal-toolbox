//! Port of `maltoolbox/language/language_graph_detector.py`.

use serde_json::json;
use std::collections::HashMap;

use super::expr_chain::ExpressionsChain;
use super::ids::AssetId;
use super::LanguageGraph;

#[derive(Debug, Clone)]
pub struct LanguageGraphContextItem {
    pub label: String,
    pub asset_type: AssetId,
    pub attack_step_name: Option<String>,
    pub expr: Option<ExpressionsChain>,
}

impl LanguageGraphContextItem {
    pub fn to_dict(&self, graph: &LanguageGraph) -> serde_json::Value {
        json!({
            "label": self.label,
            "asset_type": graph.asset(self.asset_type).name.clone(),
            "attack_step_name": self.attack_step_name,
            "expr": self.expr.as_ref().and_then(|e| e.to_dict(graph).ok()),
        })
    }
}

#[derive(Debug, Clone)]
pub struct LanguageGraphDetector {
    pub name: Option<String>,
    pub context: HashMap<String, LanguageGraphContextItem>,
    pub detector_type: Option<String>,
    /// `None` when the MAL source omits a rate; `to_dict` only emits
    /// `tprate`, never `fprate`.
    pub tprate: Option<f64>,
    pub fprate: Option<f64>,
}

impl LanguageGraphDetector {
    pub fn to_dict(&self, graph: &LanguageGraph) -> serde_json::Value {
        let mut context = serde_json::Map::new();
        for (k, v) in &self.context {
            context.insert(k.clone(), v.to_dict(graph));
        }
        json!({
            "name": self.name,
            "context": context,
            "type": self.detector_type,
            "tprate": self.tprate,
        })
    }
}
