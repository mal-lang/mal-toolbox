//! Port of `maltoolbox/language/language_graph_model_effect.py`.
//!
//! Represents the model-instance mutations ("dynamic sentences",
//! `append_reaches`/`remove_reaches`) a compromised attack step can
//! trigger: adding or removing assets/associations reachable via an
//! association-traversal chain. mal-toolbox only *builds* and *validates*
//! these structures; applying them to a live [`crate::Model`] is left to
//! a downstream consumer (e.g. mal-simulator).

use serde_json::Value;

use super::expr_chain::{ExprType, ExpressionsChain};
use super::ids::AssetId;
use super::step_expr::{process_assoc_op_step_expression, process_step_expression};
use super::{GraphError, LanguageGraph};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QuantityFilter {
    Exact(i64),
    Range(i64, i64),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssocTraversal {
    pub field_name: String,
    pub asset_filter: Option<AssetId>,
    pub quantity_filter: Option<QuantityFilter>,
}

pub fn self_traversal() -> AssocTraversal {
    AssocTraversal {
        field_name: "self".to_string(),
        asset_filter: None,
        quantity_filter: None,
    }
}

#[derive(Debug, Clone)]
pub struct GlobAssocTraversal {
    pub pattern: AssocTraversalChain,
    pub quantity_filter: Option<QuantityFilter>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SetOperation {
    Union,
    Difference,
    Intersection,
}

#[derive(Debug, Clone)]
pub struct AssocSet {
    pub set_op: SetOperation,
    pub left: AssocTraversalChain,
    pub right: AssocTraversalChain,
    pub quantity_filter: Option<QuantityFilter>,
}

#[derive(Debug, Clone)]
pub enum AssocTraversalElem {
    Traversal(AssocTraversal),
    Glob(GlobAssocTraversal),
    Set(AssocSet),
}

pub type AssocTraversalChain = Vec<AssocTraversalElem>;

#[derive(Debug, Clone)]
pub struct DynTarget {
    pub assoc_op: bool,
    pub assoc_traversal: AssocTraversalChain,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModelEffectType {
    Additive,
    Subtractive,
}

#[derive(Debug, Clone)]
pub struct LanguageGraphModelEffect {
    pub model_effect_type: ModelEffectType,
    pub base: AssocTraversalChain,
    pub targets: Vec<DynTarget>,
}

/// Port of `_parse_quantity`. A step-expression multiplicity (e.g.
/// `field:4..10`) is compiled straight from source text without
/// normalization, so `min`/`max` may still be raw strings like `"4"`
/// rather than numbers; parse both forms to mirror Python's `int(x)`.
fn value_to_i64(v: &Value) -> Result<i64, GraphError> {
    v.as_i64()
        .or_else(|| v.as_str().and_then(|s| s.parse::<i64>().ok()))
        .ok_or_else(|| GraphError::Malformed(format!("invalid quantity value: {v}")))
}

fn parse_quantity(quantity: &Value) -> Result<Option<QuantityFilter>, GraphError> {
    let min = quantity.get("min").filter(|v| !v.is_null());
    let max = quantity.get("max").filter(|v| !v.is_null());
    match (min, max) {
        (None, None) => Ok(None),
        (Some(mn), Some(mx)) => Ok(Some(QuantityFilter::Range(
            value_to_i64(mn)?,
            value_to_i64(mx)?,
        ))),
        (Some(mn), None) => Ok(Some(QuantityFilter::Exact(value_to_i64(mn)?))),
        (None, Some(_)) => Err(GraphError::Malformed(format!(
            "Invalid quantity: {quantity}"
        ))),
    }
}

/// Port of `parse_assoc_traversal`.
fn parse_assoc_traversal(
    expr_chain: Option<&ExpressionsChain>,
) -> Result<AssocTraversalChain, GraphError> {
    let Some(chain) = expr_chain else {
        return Ok(Vec::new());
    };

    match chain {
        ExpressionsChain::Binary { op, left, right } => match op {
            ExprType::Collect => {
                let mut l = parse_assoc_traversal(left.as_deref())?;
                let r = parse_assoc_traversal(right.as_deref())?;
                l.extend(r);
                Ok(l)
            }
            ExprType::Union | ExprType::Difference | ExprType::Intersection => {
                let set_op = match op {
                    ExprType::Union => SetOperation::Union,
                    ExprType::Difference => SetOperation::Difference,
                    ExprType::Intersection => SetOperation::Intersection,
                    _ => unreachable!(),
                };
                let l = parse_assoc_traversal(left.as_deref())?;
                let r = parse_assoc_traversal(right.as_deref())?;
                Ok(vec![AssocTraversalElem::Set(AssocSet {
                    set_op,
                    left: l,
                    right: r,
                    quantity_filter: None,
                })])
            }
            other => Err(GraphError::Malformed(format!(
                "Unexpected expression chain type: {:?}",
                other.as_str()
            ))),
        },
        ExpressionsChain::Field { fieldname, .. } => {
            Ok(vec![AssocTraversalElem::Traversal(AssocTraversal {
                field_name: fieldname.clone(),
                asset_filter: None,
                quantity_filter: None,
            })])
        }
        ExpressionsChain::Multiplicity { sub, multiplicity } => {
            let mut ret = parse_assoc_traversal(Some(sub))?;
            let quantity_filter = parse_quantity(multiplicity)?;
            // A multiplicity qualifier applies to whichever element type
            // is last in the chain, not just a plain field traversal.
            match ret
                .last_mut()
                .ok_or_else(|| GraphError::Malformed("empty traversal chain".into()))?
            {
                AssocTraversalElem::Traversal(t) => t.quantity_filter = quantity_filter,
                AssocTraversalElem::Glob(g) => g.quantity_filter = quantity_filter,
                AssocTraversalElem::Set(s) => s.quantity_filter = quantity_filter,
            }
            Ok(ret)
        }
        ExpressionsChain::SubType { sub, subtype } => {
            let mut ret = parse_assoc_traversal(Some(sub))?;
            match ret.last_mut() {
                Some(AssocTraversalElem::Traversal(t)) => {
                    t.asset_filter = Some(*subtype);
                }
                Some(AssocTraversalElem::Glob(g)) => match g.pattern.last_mut() {
                    Some(AssocTraversalElem::Traversal(t)) => {
                        t.asset_filter = Some(*subtype);
                    }
                    _ => {
                        return Err(GraphError::Malformed(
                            "Unexpected traversal chain structure for SUBTYPE expression".into(),
                        ))
                    }
                },
                _ => {
                    return Err(GraphError::Malformed(
                        "Unexpected traversal chain structure for SUBTYPE expression".into(),
                    ))
                }
            }
            Ok(ret)
        }
        ExpressionsChain::Transitive { sub } => {
            let pattern = parse_assoc_traversal(Some(sub))?;
            Ok(vec![AssocTraversalElem::Glob(GlobAssocTraversal {
                pattern,
                quantity_filter: None,
            })])
        }
        other => Err(GraphError::Malformed(format!(
            "Unexpected expression chain type: {:?}",
            other.expr_type()
        ))),
    }
}

/// Port of `build_assoc_traversals`.
fn build_assoc_traversals(
    expr_chain: Option<&ExpressionsChain>,
) -> Result<AssocTraversalChain, GraphError> {
    match expr_chain {
        None => Ok(vec![AssocTraversalElem::Traversal(self_traversal())]),
        Some(_) => parse_assoc_traversal(expr_chain),
    }
}

/// Port of `build_model_effect`.
pub fn build_model_effect(
    graph: &LanguageGraph,
    target_asset: AssetId,
    step_expression: &Value,
    is_additive: bool,
) -> Result<LanguageGraphModelEffect, GraphError> {
    if step_expression["type"].as_str() != Some("dyn_sentence") {
        return Err(GraphError::Malformed(
            "Only dynamic sentences can be used to build model effects".into(),
        ));
    }
    let model_effect_type = if is_additive {
        ModelEffectType::Additive
    } else {
        ModelEffectType::Subtractive
    };

    let base_expr = &step_expression["base"];
    let target_exprs = step_expression["targets"]
        .as_array()
        .cloned()
        .unwrap_or_default();

    let (base_target_asset, base_expr_chain, base_step) =
        process_step_expression(graph, target_asset, None, base_expr)?;
    if base_step.is_some() {
        return Err(GraphError::Malformed(
            "Base can not refer to an attack step in a dynamic sentence".into(),
        ));
    }
    let base = build_assoc_traversals(base_expr_chain.as_ref())?;

    let mut targets = Vec::new();
    for target_expr in &target_exprs {
        let is_assoc_op = target_expr["type"].as_str() == Some("assoc_op");
        // For link addition, the instigating asset is the one defining the
        // step; otherwise it's the asset(s) collected from the base expression.
        let starting_asset = if is_assoc_op && model_effect_type == ModelEffectType::Additive {
            target_asset
        } else {
            base_target_asset
        };
        let (_, target_expr_chain, target_step) = if is_assoc_op {
            process_assoc_op_step_expression(graph, starting_asset, None, target_expr)?
        } else {
            process_step_expression(graph, starting_asset, None, target_expr)?
        };
        if target_step.is_some() {
            return Err(GraphError::Malformed(
                "Targets can not refer to an attack step in a dynamic sentence".into(),
            ));
        }

        match target_expr_chain {
            Some(chain) => {
                let (assoc_op, unwrapped) = match chain {
                    ExpressionsChain::AssocOp { sub } => (true, Some(*sub)),
                    other => (false, Some(other)),
                };
                let assoc_traversal = build_assoc_traversals(unwrapped.as_ref())?;
                targets.push(DynTarget {
                    assoc_op,
                    assoc_traversal,
                });
            }
            None => targets.push(DynTarget {
                assoc_op: false,
                assoc_traversal: vec![AssocTraversalElem::Traversal(self_traversal())],
            }),
        }
    }

    Ok(LanguageGraphModelEffect {
        model_effect_type,
        base,
        targets,
    })
}
