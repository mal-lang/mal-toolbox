//! Port of the `follow_*_expr_chain` family in
//! `maltoolbox/attackgraph/generate.py`: walks an
//! [`ExpressionsChain`] (produced by the language graph) over a
//! [`Model`]'s actual asset-association links, resolving a starting set
//! of model assets to the set of model assets reached by that chain.

use std::collections::HashSet;

use maltoolbox_language::graph::{ExprType, ExpressionsChain};
use maltoolbox_model::Model;

use crate::GraphError;

pub fn follow_field_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    fieldname: &str,
) -> HashSet<i64> {
    let mut result = HashSet::new();
    for &asset_id in target_assets {
        if let Some(asset) = model.get_asset_by_id(asset_id) {
            if let Some(linked) = asset.associated_assets.get(fieldname) {
                result.extend(linked);
            }
        }
    }
    result
}

pub fn follow_transitive_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    sub_link: &ExpressionsChain,
) -> Result<HashSet<i64>, GraphError> {
    let mut accumulated = target_assets.clone();
    loop {
        let stepped = follow_expr_chain(model, &accumulated, Some(sub_link))?;
        let new_assets: HashSet<i64> = stepped.difference(&accumulated).copied().collect();
        if new_assets.is_empty() {
            break;
        }
        accumulated.extend(new_assets);
    }
    Ok(accumulated)
}

pub fn follow_subtype_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    sub_link: &ExpressionsChain,
    subtype: maltoolbox_language::graph::AssetId,
) -> Result<HashSet<i64>, GraphError> {
    let candidates = follow_expr_chain(model, target_assets, Some(sub_link))?;
    let mut selected = HashSet::new();
    for asset_id in candidates {
        let Some(asset) = model.get_asset_by_id(asset_id) else {
            continue;
        };
        if model.lang_graph.is_subasset_of(asset.lg_asset, subtype) {
            selected.insert(asset_id);
        }
    }
    Ok(selected)
}

pub fn follow_set_op_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    op: ExprType,
    left: Option<&ExpressionsChain>,
    right: Option<&ExpressionsChain>,
) -> Result<HashSet<i64>, GraphError> {
    let lh_targets = follow_expr_chain(model, target_assets, left)?;
    let rh_targets = follow_expr_chain(model, target_assets, right)?;

    Ok(match op {
        ExprType::Union => lh_targets.union(&rh_targets).copied().collect(),
        ExprType::Intersection => lh_targets.intersection(&rh_targets).copied().collect(),
        ExprType::Difference => lh_targets.difference(&rh_targets).copied().collect(),
        other => {
            return Err(GraphError::Malformed(format!(
                "Expr chain must be of type union, intersection or difference, got {other:?}"
            )))
        }
    })
}

pub fn follow_collect_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    left: Option<&ExpressionsChain>,
    right: Option<&ExpressionsChain>,
) -> Result<HashSet<i64>, GraphError> {
    let lh_targets = follow_expr_chain(model, target_assets, left)?;
    let mut rh_targets = HashSet::new();
    for lh_target in lh_targets {
        let singleton = HashSet::from([lh_target]);
        rh_targets.extend(follow_expr_chain(model, &singleton, right)?);
    }
    Ok(rh_targets)
}

pub fn follow_expr_chain(
    model: &Model,
    target_assets: &HashSet<i64>,
    expr_chain: Option<&ExpressionsChain>,
) -> Result<HashSet<i64>, GraphError> {
    let Some(chain) = expr_chain else {
        return Ok(target_assets.clone());
    };

    match chain {
        ExpressionsChain::Binary { op, left, right } if op.is_binary() && *op != ExprType::Collect => {
            follow_set_op_expr_chain(model, target_assets, *op, left.as_deref(), right.as_deref())
        }
        ExpressionsChain::Binary { op, left, right } if *op == ExprType::Collect => {
            follow_collect_expr_chain(model, target_assets, left.as_deref(), right.as_deref())
        }
        ExpressionsChain::Binary { op, .. } => Err(GraphError::Malformed(format!(
            "Unknown attack expressions chain type: {op:?}"
        ))),
        ExpressionsChain::Field { fieldname, .. } => {
            Ok(follow_field_expr_chain(model, target_assets, fieldname))
        }
        ExpressionsChain::Transitive { sub } => follow_transitive_expr_chain(model, target_assets, sub),
        ExpressionsChain::SubType { sub, subtype } => {
            follow_subtype_expr_chain(model, target_assets, sub, *subtype)
        }
        other => Err(GraphError::Malformed(format!(
            "Unknown attack expressions chain type: {:?}",
            other.expr_type()
        ))),
    }
}
