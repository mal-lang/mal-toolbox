//! Port of `maltoolbox/language/language_graph_attack_step.py`.
//!
//! `own_additive_model_effects`/`own_subtractive_model_effects` are not
//! part of `to_dict()`'s output in the Python original, so
//! [`LanguageGraphAttackStep::to_dict`] omits them too.

use std::collections::HashMap;
use std::rc::Rc;

use indexmap::IndexMap;
use serde_json::json;

use super::detector::LanguageGraphDetector;
use super::expr_chain::ExpressionsChain;
use super::ids::{AssetId, AttackStepId};
use super::model_effect::LanguageGraphModelEffect;
use super::{GraphError, LanguageGraph};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AttackStepType {
    Or,
    And,
    Defense,
    Exist,
    NotExist,
}

impl AttackStepType {
    pub fn as_str(self) -> &'static str {
        match self {
            AttackStepType::Or => "or",
            AttackStepType::And => "and",
            AttackStepType::Defense => "defense",
            AttackStepType::Exist => "exist",
            AttackStepType::NotExist => "notExist",
        }
    }

    pub fn parse(s: &str) -> Result<Self, GraphError> {
        match s {
            "or" => Ok(AttackStepType::Or),
            "and" => Ok(AttackStepType::And),
            "defense" => Ok(AttackStepType::Defense),
            "exist" => Ok(AttackStepType::Exist),
            "notExist" => Ok(AttackStepType::NotExist),
            other => Err(GraphError::Malformed(format!(
                "unknown attack step type: {other}"
            ))),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CausalMode {
    Action,
    Effect,
}

impl CausalMode {
    pub fn as_str(self) -> &'static str {
        match self {
            CausalMode::Action => "action",
            CausalMode::Effect => "effect",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "action" => Some(CausalMode::Action),
            "effect" => Some(CausalMode::Effect),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct LanguageGraphAttackStep {
    pub name: String,
    pub step_type: AttackStepType,
    pub asset: AssetId,
    pub causal_mode: Option<CausalMode>,
    pub ttc: Option<serde_json::Value>,
    pub overrides: bool,
    /// Insertion-ordered (like Python's `dict`): iteration order feeds
    /// node-linking order in `generate.rs` and `to_dict`'s key order.
    pub own_children: IndexMap<AttackStepId, Vec<Option<ExpressionsChain>>>,
    pub own_parents: IndexMap<AttackStepId, Vec<Option<ExpressionsChain>>>,
    pub own_additive_model_effects: Vec<LanguageGraphModelEffect>,
    pub own_subtractive_model_effects: Vec<LanguageGraphModelEffect>,
    pub info: HashMap<String, String>,
    pub inherits: Option<AttackStepId>,
    pub own_requires: Vec<ExpressionsChain>,
    pub tags: Vec<String>,
    pub detectors: IndexMap<String, LanguageGraphDetector>,
}

impl LanguageGraphAttackStep {
    pub fn full_name(&self, graph: &LanguageGraph) -> String {
        format!("{}:{}", graph.asset(self.asset).name, self.name)
    }

    /// Own + inherited children, mirroring the `children` property.
    pub fn children(
        &self,
        graph: &LanguageGraph,
    ) -> IndexMap<AttackStepId, Vec<Option<ExpressionsChain>>> {
        let mut all_children = self.own_children.clone();
        if self.overrides {
            return all_children;
        }
        let Some(inherits) = self.inherits else {
            return all_children;
        };
        let parent_step = graph.step(inherits);
        for (child, chains) in parent_step.children(graph) {
            all_children
                .entry(child)
                .and_modify(|existing| {
                    for c in &chains {
                        if !existing.iter().any(|e| expr_eq(e, c)) {
                            existing.push(c.clone());
                        }
                    }
                })
                .or_insert(chains);
        }
        all_children
    }

    /// Own + inherited requirements, mirroring the `requires` cached
    /// property.
    pub fn requires(&self, graph: &LanguageGraph) -> Vec<ExpressionsChain> {
        let mut reqs = self.own_requires.clone();
        if let Some(inherits) = self.inherits {
            reqs.extend(graph.step(inherits).requires(graph));
        }
        reqs
    }

    /// Own + inherited additive model effects, mirroring the
    /// `additive_model_effects` property.
    // TODO (from Python original): confirm whether `overrides` should
    // gate this, or only "static" (reaches) steps.
    pub fn additive_model_effects(&self, graph: &LanguageGraph) -> Vec<LanguageGraphModelEffect> {
        let mut all = self.own_additive_model_effects.clone();
        let Some(inherits) = self.inherits else {
            return all;
        };
        if self.overrides {
            return all;
        }
        all.extend(graph.step(inherits).additive_model_effects(graph));
        all
    }

    /// Own + inherited subtractive model effects, mirroring the
    /// `subtractive_model_effects` property.
    pub fn subtractive_model_effects(
        &self,
        graph: &LanguageGraph,
    ) -> Vec<LanguageGraphModelEffect> {
        let mut all = self.own_subtractive_model_effects.clone();
        let Some(inherits) = self.inherits else {
            return all;
        };
        if self.overrides {
            return all;
        }
        all.extend(graph.step(inherits).subtractive_model_effects(graph));
        all
    }

    pub fn to_dict(&self, graph: &LanguageGraph) -> Result<serde_json::Value, GraphError> {
        let mut own_children = serde_json::Map::new();
        for (child_id, chains) in &self.own_children {
            let child = graph.step(*child_id);
            let mut arr = Vec::new();
            for chain in chains {
                arr.push(match chain {
                    Some(c) => c.to_dict(graph)?,
                    None => serde_json::Value::Null,
                });
            }
            own_children.insert(child.full_name(graph), serde_json::Value::Array(arr));
        }

        let mut own_parents = serde_json::Map::new();
        for (parent_id, chains) in &self.own_parents {
            let parent = graph.step(*parent_id);
            let mut arr = Vec::new();
            for chain in chains {
                arr.push(match chain {
                    Some(c) => c.to_dict(graph)?,
                    None => serde_json::Value::Null,
                });
            }
            own_parents.insert(parent.full_name(graph), serde_json::Value::Array(arr));
        }

        let mut detectors = serde_json::Map::new();
        for (label, detector) in &self.detectors {
            detectors.insert(label.clone(), detector.to_dict(graph));
        }

        let mut node_dict = json!({
            "name": self.name,
            "type": self.step_type.as_str(),
            "asset": graph.asset(self.asset).name.clone(),
            "ttc": self.ttc,
            "own_children": own_children,
            "own_parents": own_parents,
            "info": self.info,
            "overrides": self.overrides,
            "inherits": self.inherits.map(|id| graph.step(id).full_name(graph)),
            "tags": self.tags,
            "detectors": detectors,
        });

        if !self.own_requires.is_empty() {
            let mut reqs = Vec::new();
            for req in &self.own_requires {
                reqs.push(req.to_dict(graph)?);
            }
            node_dict["requires"] = serde_json::Value::Array(reqs);
        }

        Ok(node_dict)
    }
}

/// Structural (by-value) equality for `ExpressionsChain`, used by
/// `children()`'s "already present" dedup check. Not a `PartialEq` impl
/// because `Field`'s `Rc<LanguageGraphAssociation>` is compared by
/// pointer identity here rather than derived value equality.
fn expr_eq(a: &Option<ExpressionsChain>, b: &Option<ExpressionsChain>) -> bool {
    match (a, b) {
        (None, None) => true,
        (Some(a), Some(b)) => expr_eq_inner(a, b),
        _ => false,
    }
}

fn expr_eq_inner(a: &ExpressionsChain, b: &ExpressionsChain) -> bool {
    use ExpressionsChain::*;
    match (a, b) {
        (
            Binary {
                op: op_a,
                left: left_a,
                right: right_a,
            },
            Binary {
                op: op_b,
                left: left_b,
                right: right_b,
            },
        ) => {
            op_a == op_b
                && expr_eq(&left_a.as_deref().cloned(), &left_b.as_deref().cloned())
                && expr_eq(&right_a.as_deref().cloned(), &right_b.as_deref().cloned())
        }
        (
            Field {
                association: assoc_a,
                fieldname: field_a,
            },
            Field {
                association: assoc_b,
                fieldname: field_b,
            },
        ) => Rc::ptr_eq(assoc_a, assoc_b) && field_a == field_b,
        (Transitive { sub: sub_a }, Transitive { sub: sub_b }) => expr_eq_inner(sub_a, sub_b),
        (
            SubType {
                sub: sub_a,
                subtype: subtype_a,
            },
            SubType {
                sub: sub_b,
                subtype: subtype_b,
            },
        ) => subtype_a == subtype_b && expr_eq_inner(sub_a, sub_b),
        (AssocOp { sub: sub_a }, AssocOp { sub: sub_b }) => expr_eq_inner(sub_a, sub_b),
        _ => false,
    }
}
