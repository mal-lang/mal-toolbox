//! Port of `maltoolbox/language/expression_chain.py`.
//!
//! `ExpressionsChain` represents a tree of operations describing how to
//! traverse associations in a language graph: set operations
//! (union/intersection/difference), field collection, transitive closure,
//! and subtype narrowing.

use std::collections::HashSet;
use std::rc::Rc;

use serde_json::{json, Value};

use super::assoc::LanguageGraphAssociation;
use super::ids::AssetId;
use super::GraphError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ExprType {
    Union,
    Intersection,
    Difference,
    Collect,
    Field,
    Transitive,
    SubType,
    AssocOp,
    Multiplicity,
}

impl ExprType {
    pub fn is_binary(self) -> bool {
        matches!(
            self,
            ExprType::Union | ExprType::Intersection | ExprType::Difference | ExprType::Collect
        )
    }

    pub fn as_str(self) -> &'static str {
        match self {
            ExprType::Union => "union",
            ExprType::Intersection => "intersection",
            ExprType::Difference => "difference",
            ExprType::Collect => "collect",
            ExprType::Field => "field",
            ExprType::Transitive => "transitive",
            ExprType::SubType => "subType",
            ExprType::AssocOp => "assoc_op",
            ExprType::Multiplicity => "multiplicity",
        }
    }
}

/// A single node in an expressions chain. Unlike the Python dataclass
/// (one struct with many `Option` fields, validated post-hoc), this is
/// modeled as an enum so each variant only carries the fields it needs.
#[derive(Debug, Clone)]
pub enum ExpressionsChain {
    Binary {
        op: ExprType, // one of Union/Intersection/Difference/Collect
        left: Option<Box<ExpressionsChain>>,
        right: Option<Box<ExpressionsChain>>,
    },
    Field {
        association: Rc<LanguageGraphAssociation>,
        fieldname: String,
    },
    Transitive {
        sub: Box<ExpressionsChain>,
    },
    SubType {
        sub: Box<ExpressionsChain>,
        subtype: AssetId,
    },
    AssocOp {
        sub: Box<ExpressionsChain>,
    },
    Multiplicity {
        sub: Box<ExpressionsChain>,
        multiplicity: Value,
    },
}

impl ExpressionsChain {
    pub fn expr_type(&self) -> ExprType {
        match self {
            ExpressionsChain::Binary { op, .. } => *op,
            ExpressionsChain::Field { .. } => ExprType::Field,
            ExpressionsChain::Transitive { .. } => ExprType::Transitive,
            ExpressionsChain::SubType { .. } => ExprType::SubType,
            ExpressionsChain::AssocOp { .. } => ExprType::AssocOp,
            ExpressionsChain::Multiplicity { .. } => ExprType::Multiplicity,
        }
    }

    pub fn fieldnames(&self) -> HashSet<String> {
        match self {
            ExpressionsChain::Field { fieldname, .. } => {
                let mut s = HashSet::new();
                s.insert(fieldname.clone());
                s
            }
            ExpressionsChain::Binary { left, right, .. } => {
                let mut s = chain_fieldnames(left.as_deref());
                s.extend(chain_fieldnames(right.as_deref()));
                s
            }
            ExpressionsChain::Transitive { sub }
            | ExpressionsChain::SubType { sub, .. }
            | ExpressionsChain::AssocOp { sub }
            | ExpressionsChain::Multiplicity { sub, .. } => chain_fieldnames(Some(sub)),
        }
    }

    pub fn is_additive(&self) -> bool {
        match self {
            ExpressionsChain::Binary { op, left, right } => match op {
                ExprType::Intersection | ExprType::Difference => false,
                _ => chain_is_additive(left.as_deref()) && chain_is_additive(right.as_deref()),
            },
            ExpressionsChain::Field { .. } => true,
            ExpressionsChain::Transitive { sub }
            | ExpressionsChain::SubType { sub, .. }
            | ExpressionsChain::AssocOp { sub }
            | ExpressionsChain::Multiplicity { sub, .. } => chain_is_additive(Some(sub)),
        }
    }

    /// Mirrors `ExpressionsChain.to_dict`. Errors on `Multiplicity` chains,
    /// which are only ever consumed by model-effect processing and never
    /// serialized directly as a reaches/requires chain.
    pub fn to_dict(&self, graph: &super::LanguageGraph) -> Result<Value, GraphError> {
        match self {
            ExpressionsChain::Binary { op, left, right } => Ok(json!({
                op.as_str(): {
                    "left": match left { Some(l) => l.to_dict(graph)?, None => json!({}) },
                    "right": match right { Some(r) => r.to_dict(graph)?, None => json!({}) },
                },
                "type": op.as_str(),
            })),
            ExpressionsChain::Field {
                association,
                fieldname,
            } => {
                let asset_type = association.resolve_field_asset_type(graph, fieldname)?;
                Ok(json!({
                    association.name.clone(): {
                        "fieldname": fieldname,
                        "asset type": asset_type,
                    },
                    "type": ExprType::Field.as_str(),
                }))
            }
            ExpressionsChain::Transitive { sub } => Ok(json!({
                "transitive": sub.to_dict(graph)?,
                "type": ExprType::Transitive.as_str(),
            })),
            ExpressionsChain::SubType { sub, subtype } => Ok(json!({
                "subType": graph.asset(*subtype).name.clone(),
                "expression": sub.to_dict(graph)?,
                "type": ExprType::SubType.as_str(),
            })),
            ExpressionsChain::AssocOp { sub } => Ok(json!({
                "operand": sub.to_dict(graph)?,
                "type": ExprType::AssocOp.as_str(),
            })),
            ExpressionsChain::Multiplicity { .. } => Err(GraphError::Malformed(
                "Unknown expressions chain element multiplicity".into(),
            )),
        }
    }
}

pub fn chain_fieldnames(expr_chain: Option<&ExpressionsChain>) -> HashSet<String> {
    expr_chain
        .map(ExpressionsChain::fieldnames)
        .unwrap_or_default()
}

pub fn chain_is_additive(expr_chain: Option<&ExpressionsChain>) -> bool {
    expr_chain
        .map(ExpressionsChain::is_additive)
        .unwrap_or(true)
}
