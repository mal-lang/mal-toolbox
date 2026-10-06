//! Port of `maltoolbox/attackgraph/partially_generate.py`: incrementally
//! update an [`crate::AttackGraph`] in response to model changes, instead
//! of a full [`crate::generate::generate_graph`] rebuild.

use std::collections::{HashMap, HashSet};

use indexmap::IndexMap;

use maltoolbox_language::graph::step_expr::reverse_expr_chain;
use maltoolbox_language::graph::{AssetId, ExprType, ExpressionsChain};
use maltoolbox_model::{AssetSnapshot, Model};
use slotmap::SlotMap;

use crate::expr_follow::follow_expr_chain;
use crate::ids::AttackGraphNodeId;
use crate::node::AttackGraphNode;
use crate::GraphError;

/// `affected_assoc_dict`: per model-asset-id, per-fieldname, the set of
/// other asset ids an association add/remove touched.
pub type AssocAffectedDict = HashMap<i64, HashMap<String, HashSet<i64>>>;

pub fn switch_fieldname(
    model: &Model,
    asset_id: i64,
    fieldname: &str,
) -> Result<String, GraphError> {
    let asset = model
        .get_asset_by_id(asset_id)
        .ok_or_else(|| GraphError::Malformed(format!("Unknown asset id {asset_id}")))?;
    switch_fieldname_for_lg_asset(model, asset.lg_asset, &asset.name, fieldname)
}

/// Same lookup as `switch_fieldname`, but keyed off an already-known
/// language-graph asset type + name rather than an instance id, so it
/// works even if the asset has been removed from `model` (the caller
/// supplies the type/name from an [`AssetSnapshot`]).
fn switch_fieldname_for_lg_asset(
    model: &Model,
    lg_asset: AssetId,
    asset_name: &str,
    fieldname: &str,
) -> Result<String, GraphError> {
    let assoc = model
        .lang_graph
        .associations(lg_asset)
        .get(fieldname)
        .cloned()
        .ok_or_else(|| {
            GraphError::Malformed(format!(
                "Fieldname {fieldname} not found in associations of asset {asset_name}"
            ))
        })?;
    if fieldname == assoc.left_field.fieldname {
        Ok(assoc.right_field.fieldname.clone())
    } else if fieldname == assoc.right_field.fieldname {
        Ok(assoc.left_field.fieldname.clone())
    } else {
        Err(GraphError::Malformed(format!(
            "Fieldname {fieldname} not found in association {}",
            assoc.name
        )))
    }
}

/// Resolves the opposite fieldname for `(asset_id, fieldname)`, where
/// `asset_id` may already have been removed from `model` - in which case
/// `removed` must contain its snapshot.
pub fn switch_fieldname_possibly_removed(
    model: &Model,
    asset_id: i64,
    fieldname: &str,
    removed: &HashMap<i64, AssetSnapshot>,
) -> Result<String, GraphError> {
    if let Some(snapshot) = removed.get(&asset_id) {
        switch_fieldname_for_lg_asset(model, snapshot.lg_asset, &snapshot.name, fieldname)
    } else {
        switch_fieldname(model, asset_id, fieldname)
    }
}

/// Recompute `affected_key`'s children from the model's current
/// associations (the expression chain's actual target may be several
/// hops past the association that changed), and reconcile against what
/// is currently linked.
pub fn correct_node_children_on_modified_assoc(
    model: &Model,
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    affected_key: AttackGraphNodeId,
    full_name_to_node: &IndexMap<String, AttackGraphNodeId>,
) -> Result<(), GraphError> {
    let (model_asset_id, lg_attack_step_id) = {
        let node = &nodes[affected_key];
        let asset_id = node.model_asset.ok_or_else(|| {
            GraphError::Malformed("Attack graph node is missing asset link".into())
        })?;
        (asset_id, node.lg_attack_step)
    };

    let children = model
        .lang_graph
        .step(lg_attack_step_id)
        .children(&model.lang_graph);

    let mut correct_children: HashSet<AttackGraphNodeId> = HashSet::new();
    for (child_lg_step, chains) in children {
        let child_step_name = model.lang_graph.step(child_lg_step).name.clone();
        for chain in chains {
            let target_assets =
                follow_expr_chain(model, &HashSet::from([model_asset_id]), chain.as_ref())?;
            for target_asset_id in target_assets {
                let target_asset = model
                    .get_asset_by_id(target_asset_id)
                    .expect("follow_expr_chain only returns existing asset ids");
                let full_name = format!("{}:{child_step_name}", target_asset.name);
                let target_key = *full_name_to_node.get(&full_name).ok_or_else(|| {
                    let node = &nodes[affected_key];
                    let owner_name = model
                        .get_asset_by_id(model_asset_id)
                        .map(|a| a.name.as_str())
                        .unwrap_or("?");
                    let affected_full_name = format!("{owner_name}:{}", node.name);
                    GraphError::Malformed(format!(
                        "Failed to find target node \"{full_name}\" for \"{affected_full_name}\"({})",
                        node.id
                    ))
                })?;
                correct_children.insert(target_key);
            }
        }
    }

    let current_children = nodes[affected_key].children.clone();

    for &target_key in correct_children.difference(&current_children) {
        nodes[affected_key].children.insert(target_key);
        nodes[target_key].parents.insert(affected_key);
    }
    for &target_key in current_children.difference(&correct_children) {
        nodes[affected_key].children.remove(&target_key);
        nodes[target_key].parents.remove(&affected_key);
    }

    Ok(())
}

/// `removed_assets` carries a [`AssetSnapshot`] per id rather than a bare
/// `HashSet<i64>` so this works for ids already gone from `model`; only
/// `model.lang_graph` (unaffected by instance-model mutation) is needed.
pub fn nodes_to_be_removed(
    removed_assets: &HashMap<i64, AssetSnapshot>,
    model: &Model,
    full_name_to_node: &IndexMap<String, AttackGraphNodeId>,
) -> Result<HashSet<AttackGraphNodeId>, GraphError> {
    let mut removal_candidates = HashSet::new();
    for snapshot in removed_assets.values() {
        let lg_step_ids: Vec<_> = model
            .lang_graph
            .asset(snapshot.lg_asset)
            .attack_steps
            .values()
            .copied()
            .collect();
        for lg_step_id in lg_step_ids {
            let lg_step = model.lang_graph.step(lg_step_id);
            let full_name = format!("{}:{}", snapshot.name, lg_step.name);
            let node_key = full_name_to_node.get(&full_name).copied().ok_or_else(|| {
                GraphError::Malformed(format!(
                    "Failed to find {} for removed asset {}.",
                    lg_step.full_name(&model.lang_graph),
                    snapshot.name
                ))
            })?;
            removal_candidates.insert(node_key);
        }
    }
    Ok(removal_candidates)
}

pub fn assoc_affected_expr_chain(
    model: &Model,
    instigating_assets: &HashSet<i64>,
    affected_assoc_dict: &AssocAffectedDict,
    expr_chain: Option<&ExpressionsChain>,
) -> Result<bool, GraphError> {
    let modified_fieldnames: HashSet<String> = affected_assoc_dict
        .values()
        .flat_map(|fields| fields.keys().cloned())
        .collect();
    assoc_affected_expr_chain_inner(
        model,
        instigating_assets,
        affected_assoc_dict,
        expr_chain,
        &modified_fieldnames,
    )
}

fn assoc_affected_expr_chain_inner(
    model: &Model,
    instigating_assets: &HashSet<i64>,
    affected_assoc_dict: &AssocAffectedDict,
    expr_chain: Option<&ExpressionsChain>,
    modified_fieldnames: &HashSet<String>,
) -> Result<bool, GraphError> {
    let Some(chain) = expr_chain else {
        return Ok(false);
    };
    if instigating_assets.is_empty() {
        return Ok(false);
    }
    if chain.fieldnames().is_disjoint(modified_fieldnames) {
        return Ok(false);
    }

    match chain {
        ExpressionsChain::Field { fieldname, .. } => {
            Ok(instigating_assets.iter().any(|asset_id| {
                affected_assoc_dict
                    .get(asset_id)
                    .map(|fields| fields.contains_key(fieldname))
                    .unwrap_or(false)
            }))
        }
        ExpressionsChain::Binary { op, left, right } if *op != ExprType::Collect => {
            Ok(assoc_affected_expr_chain_inner(
                model,
                instigating_assets,
                affected_assoc_dict,
                left.as_deref(),
                modified_fieldnames,
            )? || assoc_affected_expr_chain_inner(
                model,
                instigating_assets,
                affected_assoc_dict,
                right.as_deref(),
                modified_fieldnames,
            )?)
        }
        ExpressionsChain::Binary { op, left, right } if *op == ExprType::Collect => {
            use maltoolbox_language::graph::expr_chain::chain_fieldnames;
            if !chain_fieldnames(left.as_deref()).is_disjoint(modified_fieldnames)
                && assoc_affected_expr_chain_inner(
                    model,
                    instigating_assets,
                    affected_assoc_dict,
                    left.as_deref(),
                    modified_fieldnames,
                )?
            {
                return Ok(true);
            }
            if chain_fieldnames(right.as_deref()).is_disjoint(modified_fieldnames) {
                return Ok(false);
            }
            let next_assets = follow_expr_chain(model, instigating_assets, left.as_deref())?;
            assoc_affected_expr_chain_inner(
                model,
                &next_assets,
                affected_assoc_dict,
                right.as_deref(),
                modified_fieldnames,
            )
        }
        ExpressionsChain::SubType { sub, .. } => assoc_affected_expr_chain_inner(
            model,
            instigating_assets,
            affected_assoc_dict,
            Some(sub),
            modified_fieldnames,
        ),
        ExpressionsChain::Transitive { sub } => {
            let mut frontier = instigating_assets.clone();
            let mut visited: HashSet<i64> = HashSet::new();
            while !frontier.is_empty() {
                if assoc_affected_expr_chain_inner(
                    model,
                    &frontier,
                    affected_assoc_dict,
                    Some(sub),
                    modified_fieldnames,
                )? {
                    return Ok(true);
                }
                visited.extend(&frontier);
                let stepped = follow_expr_chain(model, &frontier, Some(sub))?;
                frontier = stepped.difference(&visited).copied().collect();
            }
            Ok(false)
        }
        other => Err(GraphError::Malformed(format!(
            "Unknown expression chain type: {:?}",
            other.expr_type()
        ))),
    }
}

pub fn assoc_left_assets(
    model: &Model,
    affected_assoc_dict: &AssocAffectedDict,
    expr_chain: Option<&ExpressionsChain>,
    modified_fieldnames: &HashSet<String>,
) -> Result<HashSet<i64>, GraphError> {
    let Some(chain) = expr_chain else {
        return Ok(HashSet::new());
    };
    if chain.fieldnames().is_disjoint(modified_fieldnames) {
        return Ok(HashSet::new());
    }

    use maltoolbox_language::graph::expr_chain::chain_fieldnames;

    match chain {
        ExpressionsChain::Field {
            association,
            fieldname,
        } => Ok(affected_assoc_dict
            .iter()
            .filter(|(asset_id, fields)| {
                fields.contains_key(fieldname)
                    && model
                        .get_asset_by_id(**asset_id)
                        .and_then(|a| {
                            model
                                .lang_graph
                                .associations(a.lg_asset)
                                .get(fieldname)
                                .cloned()
                        })
                        .map(|a| *a == **association)
                        .unwrap_or(false)
            })
            .map(|(asset_id, _)| *asset_id)
            .collect()),
        ExpressionsChain::Binary { op, left, right } if *op != ExprType::Collect => {
            let mut result = assoc_left_assets(
                model,
                affected_assoc_dict,
                left.as_deref(),
                modified_fieldnames,
            )?;
            result.extend(assoc_left_assets(
                model,
                affected_assoc_dict,
                right.as_deref(),
                modified_fieldnames,
            )?);
            Ok(result)
        }
        ExpressionsChain::Binary { op, left, right } if *op == ExprType::Collect => {
            let mut roots = HashSet::new();
            if !chain_fieldnames(left.as_deref()).is_disjoint(modified_fieldnames) {
                roots.extend(assoc_left_assets(
                    model,
                    affected_assoc_dict,
                    left.as_deref(),
                    modified_fieldnames,
                )?);
            }
            if !chain_fieldnames(right.as_deref()).is_disjoint(modified_fieldnames) {
                let right_roots = assoc_left_assets(
                    model,
                    affected_assoc_dict,
                    right.as_deref(),
                    modified_fieldnames,
                )?;
                if !right_roots.is_empty() {
                    let reverse_left = reverse_expr_chain(left.as_deref())?;
                    roots.extend(follow_expr_chain(
                        model,
                        &right_roots,
                        reverse_left.as_ref(),
                    )?);
                }
            }
            Ok(roots)
        }
        ExpressionsChain::SubType { sub, .. } => {
            assoc_left_assets(model, affected_assoc_dict, Some(sub), modified_fieldnames)
        }
        ExpressionsChain::Transitive { sub } => {
            let seed_roots =
                assoc_left_assets(model, affected_assoc_dict, Some(sub), modified_fieldnames)?;
            let reverse_sub = reverse_expr_chain(Some(sub))?;
            let mut roots = seed_roots.clone();
            let mut frontier = seed_roots;
            while !frontier.is_empty() {
                let stepped = follow_expr_chain(model, &frontier, reverse_sub.as_ref())?;
                frontier = stepped.difference(&roots).copied().collect();
                roots.extend(&frontier);
            }
            Ok(roots)
        }
        other => Err(GraphError::Malformed(format!(
            "Unknown expression chain type: {:?}",
            other.expr_type()
        ))),
    }
}

pub fn assoc_affected_nodes(
    model: &Model,
    affected_assoc_dict: &AssocAffectedDict,
    full_name_to_node: &IndexMap<String, AttackGraphNodeId>,
) -> Result<HashSet<AttackGraphNodeId>, GraphError> {
    let modified_fieldnames: HashSet<String> = affected_assoc_dict
        .values()
        .flat_map(|fields| fields.keys().cloned())
        .collect();

    let candidate_map = model.lang_graph.fieldname_to_candidate_steps();
    let mut candidate_steps: HashSet<(String, String)> = HashSet::new();
    for fieldname in &modified_fieldnames {
        if let Some(steps) = candidate_map.get(fieldname) {
            candidate_steps.extend(steps.iter().cloned());
        }
    }

    let mut assets_by_type: Option<HashMap<String, Vec<i64>>> = None;

    let mut ret_nodes = HashSet::new();
    for (asset_type, step_name) in candidate_steps {
        let Some(asset_type_id) = model.lang_graph.asset_id(&asset_type) else {
            continue;
        };
        let Some(&lg_step_id) = model
            .lang_graph
            .asset(asset_type_id)
            .attack_steps
            .get(&step_name)
        else {
            continue;
        };
        let lg_step = model.lang_graph.step(lg_step_id);

        let mut affected_assets: HashSet<i64> = HashSet::new();
        for chains in lg_step.children(&model.lang_graph).values() {
            for chain in chains {
                let Some(chain) = chain else { continue };
                if chain.is_additive() {
                    affected_assets.extend(assoc_left_assets(
                        model,
                        affected_assoc_dict,
                        Some(chain),
                        &modified_fieldnames,
                    )?);
                    continue;
                }
                if assets_by_type.is_none() {
                    let mut by_type: HashMap<String, Vec<i64>> = HashMap::new();
                    for &asset_id in &model.asset_order {
                        let asset = &model.assets[&asset_id];
                        by_type
                            .entry(asset.asset_type.clone())
                            .or_default()
                            .push(asset_id);
                    }
                    assets_by_type = Some(by_type);
                }
                if let Some(candidates) = assets_by_type.as_ref().and_then(|m| m.get(&asset_type)) {
                    for &asset_id in candidates {
                        if assoc_affected_expr_chain(
                            model,
                            &HashSet::from([asset_id]),
                            affected_assoc_dict,
                            Some(chain),
                        )? {
                            affected_assets.insert(asset_id);
                        }
                    }
                }
            }
        }

        for asset_id in affected_assets {
            let asset = &model.assets[&asset_id];
            if !model
                .lang_graph
                .asset(asset.lg_asset)
                .attack_steps
                .contains_key(&step_name)
            {
                continue;
            }
            let full_name = format!("{}:{step_name}", asset.name);
            if let Some(&node_key) = full_name_to_node.get(&full_name) {
                ret_nodes.insert(node_key);
            }
        }
    }
    Ok(ret_nodes)
}
