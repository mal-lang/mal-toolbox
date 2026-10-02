//! Port of `maltoolbox/attackgraph/generate.py`.

use std::collections::{HashMap, HashSet};

use maltoolbox_language::graph::attack_step::AttackStepType;
use maltoolbox_language::graph::AttackStepId;
use maltoolbox_model::Model;
use serde_json::Map;
use slotmap::SlotMap;

use crate::detector::Detector;
use crate::expr_follow::follow_expr_chain;
use crate::ids::AttackGraphNodeId;
use crate::node::AttackGraphNode;
use crate::ttcs::get_ttc_dist;
use crate::GraphError;

pub struct GeneratedGraph {
    pub nodes: SlotMap<AttackGraphNodeId, AttackGraphNode>,
    pub id_to_node: HashMap<i64, AttackGraphNodeId>,
    pub attack_steps: Vec<AttackGraphNodeId>,
    pub defense_steps: Vec<AttackGraphNodeId>,
    pub full_name_to_node: HashMap<String, AttackGraphNodeId>,
}

/// Just-created nodes, as produced by [`create_nodes_for`] directly into
/// a caller-supplied `SlotMap` (as opposed to [`GeneratedGraph`], which
/// owns a fresh one) - the shape partial regeneration needs, since
/// slotmap keys are only valid within the `SlotMap` instance that
/// created them and can't be transplanted into a different one the way
/// Python's plain integer-keyed dicts can.
pub struct CreatedNodes {
    pub id_to_node: HashMap<i64, AttackGraphNodeId>,
    pub full_name_to_node: HashMap<String, AttackGraphNodeId>,
    pub attack_steps: Vec<AttackGraphNodeId>,
    pub defense_steps: Vec<AttackGraphNodeId>,
}

/// Existence status for `exist`/`notExist` steps: `true` if any
/// requirement expression resolves to at least one target asset, `false`
/// if all are empty, `None` for other step types.
pub fn get_existence_status(
    model: &Model,
    asset_id: i64,
    lg_step_id: AttackStepId,
) -> Result<Option<bool>, GraphError> {
    let lg_step = model.lang_graph.step(lg_step_id);
    if !matches!(lg_step.step_type, AttackStepType::Exist | AttackStepType::NotExist) {
        return Ok(None);
    }

    for requirement in lg_step.requires(&model.lang_graph) {
        let targets = follow_expr_chain(model, &HashSet::from([asset_id]), Some(&requirement))?;
        if !targets.is_empty() {
            return Ok(Some(true));
        }
    }
    Ok(Some(false))
}

pub fn create_nodes_from_model(
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    model: &Model,
) -> Result<CreatedNodes, GraphError> {
    create_nodes_for(nodes, model.asset_order.iter().copied(), 0, model)
}

/// Port of `partially_generate.py`'s `create_nodes_from_assets`: build
/// nodes only for `asset_ids`, continuing node-id assignment from
/// `starting_id`. Shares the node-building logic with
/// `create_nodes_from_model` via `create_nodes_for`.
pub fn create_nodes_from_assets(
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    asset_ids: &std::collections::HashSet<i64>,
    starting_id: i64,
    model: &Model,
) -> Result<CreatedNodes, GraphError> {
    create_nodes_for(nodes, asset_ids.iter().copied(), starting_id, model)
}

fn create_nodes_for(
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    asset_ids: impl Iterator<Item = i64>,
    starting_id: i64,
    model: &Model,
) -> Result<CreatedNodes, GraphError> {
    let mut id_to_node = HashMap::new();
    let mut full_name_to_node = HashMap::new();
    let mut attack_steps = Vec::new();
    let mut defense_steps = Vec::new();
    let mut node_id: i64 = starting_id;

    for asset_id in asset_ids {
        let asset = &model.assets[&asset_id];
        let lg_step_ids: Vec<AttackStepId> = model
            .lang_graph
            .asset(asset.lg_asset)
            .attack_steps
            .values()
            .copied()
            .collect();

        for lg_step_id in lg_step_ids {
            let lg_step = model.lang_graph.step(lg_step_id);
            let full_name = format!("{}:{}", asset.name, lg_step.name);
            let existence_status = get_existence_status(model, asset_id, lg_step_id)?;

            let node = AttackGraphNode {
                id: node_id,
                lg_attack_step: lg_step_id,
                name: lg_step.name.clone(),
                step_type: lg_step.step_type,
                causal_mode: lg_step.causal_mode,
                ttc: get_ttc_dist(asset, lg_step),
                tags: lg_step.tags.clone(),
                additive_model_effects: crate::node::non_empty(
                    lg_step.additive_model_effects(&model.lang_graph),
                ),
                subtractive_model_effects: crate::node::non_empty(
                    lg_step.subtractive_model_effects(&model.lang_graph),
                ),
                model_asset: Some(asset_id),
                existence_status,
                children: HashSet::new(),
                parents: HashSet::new(),
                extras: Map::new(),
                detectors: HashMap::new(),
                full_name_override: None,
            };

            let step_type = node.step_type;
            let key = nodes.insert(node);
            id_to_node.insert(node_id, key);
            full_name_to_node.insert(full_name, key);
            match step_type {
                AttackStepType::Or | AttackStepType::And => attack_steps.push(key),
                AttackStepType::Defense => defense_steps.push(key),
                _ => {}
            }
            node_id += 1;
        }
    }

    Ok(CreatedNodes {
        id_to_node,
        full_name_to_node,
        attack_steps,
        defense_steps,
    })
}

/// Port of `link_node_children`. Unlike the Python original, this calls
/// `LanguageGraphAttackStep::children` (already own+inherited, unless
/// overridden) exactly once rather than additionally walking the
/// `inherits` chain and recombining at each ancestor: that walk recomputes
/// children `children()` already includes recursively, and since
/// `ag_node.children`/`target_node.parents` are sets, the duplicate adds
/// it produces are no-ops. The two are behaviorally identical; this port
/// skips the redundant work.
pub fn link_node_children(
    model: &Model,
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    ag_node_key: AttackGraphNodeId,
    full_name_to_node: &HashMap<String, AttackGraphNodeId>,
) -> Result<(), GraphError> {
    let (model_asset_id, lg_attack_step_id) = {
        let node = &nodes[ag_node_key];
        let asset_id = node
            .model_asset
            .ok_or_else(|| GraphError::Malformed("Attack graph node is missing asset link".into()))?;
        (asset_id, node.lg_attack_step)
    };

    let children = model.lang_graph.step(lg_attack_step_id).children(&model.lang_graph);

    for (child_lg_step, chains) in children {
        let child_step_name = model.lang_graph.step(child_lg_step).name.clone();
        for chain in chains {
            link_from_expr_chain(
                model,
                nodes,
                ag_node_key,
                model_asset_id,
                &child_step_name,
                chain.as_ref(),
                full_name_to_node,
            )?;
        }
    }
    Ok(())
}

fn link_from_expr_chain(
    model: &Model,
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    ag_node_key: AttackGraphNodeId,
    model_asset_id: i64,
    child_step_name: &str,
    expr_chain: Option<&maltoolbox_language::graph::ExpressionsChain>,
    full_name_to_node: &HashMap<String, AttackGraphNodeId>,
) -> Result<(), GraphError> {
    let target_assets = follow_expr_chain(model, &HashSet::from([model_asset_id]), expr_chain)?;

    for target_asset_id in target_assets {
        let target_asset = model
            .get_asset_by_id(target_asset_id)
            .expect("follow_expr_chain only returns existing asset ids");
        let full_name = format!("{}:{child_step_name}", target_asset.name);

        let target_key = *full_name_to_node.get(&full_name).ok_or_else(|| {
            let (ag_full_name, ag_id) = {
                let node = &nodes[ag_node_key];
                let owner_name = model
                    .get_asset_by_id(model_asset_id)
                    .map(|a| a.name.as_str())
                    .unwrap_or("?");
                (format!("{owner_name}:{}", node.name), node.id)
            };
            GraphError::StepExpression(format!(
                "Failed to find target node \"{full_name}\" for \"{ag_full_name}\"({ag_id})"
            ))
        })?;

        nodes[ag_node_key].children.insert(target_key);
        nodes[target_key].parents.insert(ag_node_key);
    }
    Ok(())
}

pub fn link_nodes_by_language(
    model: &Model,
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    full_name_to_node: &HashMap<String, AttackGraphNodeId>,
) -> Result<(), GraphError> {
    let keys: Vec<AttackGraphNodeId> = full_name_to_node.values().copied().collect();
    for key in keys {
        link_node_children(model, nodes, key, full_name_to_node)?;
    }
    Ok(())
}

fn get_potential_context(
    model: &Model,
    asset_id: i64,
    full_name_to_node: &HashMap<String, AttackGraphNodeId>,
    lg_detector: &maltoolbox_language::graph::LanguageGraphDetector,
) -> Result<HashMap<String, HashSet<AttackGraphNodeId>>, GraphError> {
    let mut context: HashMap<String, HashSet<AttackGraphNodeId>> = HashMap::new();
    for (label, item) in &lg_detector.context {
        let targets = follow_expr_chain(model, &HashSet::from([asset_id]), item.expr.as_ref())?;
        for target_asset_id in targets {
            let target_asset = model
                .get_asset_by_id(target_asset_id)
                .expect("follow_expr_chain only returns existing asset ids");
            let step_name = item.attack_step_name.clone().unwrap_or_default();
            let full_name = format!("{}:{step_name}", target_asset.name);
            let target_key = *full_name_to_node.get(&full_name).ok_or_else(|| {
                GraphError::Malformed(format!(
                    "Failed to find target node for context item \"{label}\" with asset \"{}\" and attack step \"{step_name}\"",
                    target_asset.name
                ))
            })?;
            context.entry(label.clone()).or_default().insert(target_key);
        }
    }
    Ok(context)
}

pub fn create_detectors(
    nodes: &mut SlotMap<AttackGraphNodeId, AttackGraphNode>,
    full_name_to_node: &HashMap<String, AttackGraphNodeId>,
    model: &Model,
) -> Result<(), GraphError> {
    let node_keys: Vec<AttackGraphNodeId> = full_name_to_node.values().copied().collect();

    for node_key in node_keys {
        let (model_asset_id, lg_step_id) = {
            let node = &nodes[node_key];
            let asset_id = node
                .model_asset
                .ok_or_else(|| GraphError::Malformed("Attack graph node is missing asset link".into()))?;
            (asset_id, node.lg_attack_step)
        };

        let lg_detectors = model.lang_graph.step(lg_step_id).detectors.clone();
        let mut node_detectors = HashMap::new();
        for (label, lg_detector) in &lg_detectors {
            let potential_context =
                get_potential_context(model, model_asset_id, full_name_to_node, lg_detector)?;
            node_detectors.insert(
                label.clone(),
                Detector {
                    name: lg_detector.name.clone(),
                    node: node_key,
                    potential_context,
                    tprate: lg_detector.tprate,
                    fprate: lg_detector.fprate,
                },
            );
        }
        nodes[node_key].detectors = node_detectors;
    }
    Ok(())
}

pub fn generate_graph(model: &Model) -> Result<GeneratedGraph, GraphError> {
    let mut nodes = SlotMap::with_key();
    let created = create_nodes_from_model(&mut nodes, model)?;
    link_nodes_by_language(model, &mut nodes, &created.full_name_to_node)?;
    create_detectors(&mut nodes, &created.full_name_to_node, model)?;
    Ok(GeneratedGraph {
        nodes,
        id_to_node: created.id_to_node,
        attack_steps: created.attack_steps,
        defense_steps: created.defense_steps,
        full_name_to_node: created.full_name_to_node,
    })
}
