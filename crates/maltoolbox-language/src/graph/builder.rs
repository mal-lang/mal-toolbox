//! Port of `maltoolbox/language/language_graph_builder.py`.
//!
//! Asset creation and inheritance, associations, variables, attack step
//! creation and inheritance, `reaches`/`requires` connection, and model
//! effects (`append_reaches`/`remove_reaches`, via
//! [`connect_model_effects`] + [`assoc_traversal::validate_model_effects`])
//! are all ported.

use std::collections::{HashMap, VecDeque};
use std::rc::Rc;

use serde_json::Value;

use super::assoc::{LanguageGraphAssociation, LanguageGraphAssociationField};
use super::attack_step::{AttackStepType, CausalMode, LanguageGraphAttackStep};
use super::detector::{LanguageGraphContextItem, LanguageGraphDetector};
use super::ids::{AssetId, AttackStepId};
use super::step_expr::{process_step_expression, reverse_expr_chain, resolve_variable};
use super::{asset::LanguageGraphAsset, assoc_traversal, model_effect, GraphError, LanguageGraph};

fn meta_map(v: &Value) -> HashMap<String, String> {
    v.as_object()
        .into_iter()
        .flatten()
        .filter_map(|(k, v)| v.as_str().map(|s| (k.clone(), s.to_string())))
        .collect()
}

pub fn generate_graph(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    create_lg_assets(graph)?;
    link_assets(graph)?;
    create_associations_for_assets(graph)?;
    set_variables_for_assets(graph)?;
    generate_attack_steps(graph)?;
    Ok(())
}

fn create_lg_assets(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let assets_spec = graph.lang_spec["assets"].as_array().cloned().unwrap_or_default();
    for asset_dict in &assets_spec {
        let name = asset_dict["name"]
            .as_str()
            .ok_or_else(|| GraphError::Malformed("asset missing name".into()))?
            .to_string();
        let node = LanguageGraphAsset {
            name: name.clone(),
            own_associations: HashMap::new(),
            attack_steps: HashMap::new(),
            info: meta_map(&asset_dict["meta"]),
            own_super_asset: None,
            own_sub_assets: Vec::new(),
            own_variables: HashMap::new(),
            is_abstract: asset_dict["isAbstract"].as_bool().unwrap_or(false),
        };
        let id = graph.assets.insert(node);
        graph.asset_id_by_name.insert(name, id);
        graph.asset_order.push(id);
    }
    Ok(())
}

fn link_assets(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let assets_spec = graph.lang_spec["assets"].as_array().cloned().unwrap_or_default();
    for asset_dict in &assets_spec {
        let name = asset_dict["name"].as_str().unwrap_or_default();
        let asset_id = *graph.asset_id_by_name.get(name).unwrap();

        let Some(super_name) = asset_dict["superAsset"].as_str() else {
            continue;
        };
        let super_id = graph.asset_id_by_name.get(super_name).copied().ok_or_else(|| {
            GraphError::SuperAssetNotFound {
                asset_name: name.to_string(),
                super_name: super_name.to_string(),
            }
        })?;

        graph.assets[super_id].own_sub_assets.push(asset_id);
        graph.assets[asset_id].own_super_asset = Some(super_id);
    }
    Ok(())
}

fn create_associations_for_assets(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let associations_spec = graph.lang_spec["associations"].as_array().cloned().unwrap_or_default();
    for assoc_dict in &associations_spec {
        let name = assoc_dict["name"].as_str().unwrap_or_default().to_string();
        let left_asset_name = assoc_dict["leftAsset"].as_str().unwrap_or_default();
        let right_asset_name = assoc_dict["rightAsset"].as_str().unwrap_or_default();

        let left_asset_id = graph.asset_id_by_name.get(left_asset_name).copied().ok_or_else(|| {
            GraphError::AssociationAssetNotFound {
                assoc_name: name.clone(),
                asset_name: left_asset_name.to_string(),
            }
        })?;
        let right_asset_id = graph.asset_id_by_name.get(right_asset_name).copied().ok_or_else(|| {
            GraphError::AssociationAssetNotFound {
                assoc_name: name.clone(),
                asset_name: right_asset_name.to_string(),
            }
        })?;

        let left_field = LanguageGraphAssociationField {
            asset: left_asset_id,
            fieldname: assoc_dict["leftField"].as_str().unwrap_or_default().to_string(),
            minimum: assoc_dict["leftMultiplicity"]["min"].as_i64().unwrap_or(0),
            maximum: assoc_dict["leftMultiplicity"]["max"].as_i64(),
        };
        let right_field = LanguageGraphAssociationField {
            asset: right_asset_id,
            fieldname: assoc_dict["rightField"].as_str().unwrap_or_default().to_string(),
            minimum: assoc_dict["rightMultiplicity"]["min"].as_i64().unwrap_or(0),
            maximum: assoc_dict["rightMultiplicity"]["max"].as_i64(),
        };

        let assoc = Rc::new(LanguageGraphAssociation {
            name,
            left_field,
            right_field,
            info: meta_map(&assoc_dict["meta"]),
        });

        let left_fieldname = assoc.left_field.fieldname.clone();
        let right_fieldname = assoc.right_field.fieldname.clone();
        graph.assets[left_asset_id]
            .own_associations
            .insert(right_fieldname, assoc.clone());
        graph.assets[right_asset_id]
            .own_associations
            .insert(left_fieldname, assoc);
    }
    Ok(())
}

fn set_variables_for_assets(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let order = graph.asset_order.clone();
    for asset_id in order {
        let asset_name = graph.asset(asset_id).name.clone();
        let variables = super::lookup::get_variables_for_asset_type(&asset_name, &graph.lang_spec)?;
        for var in &variables {
            let var_name = var["name"]
                .as_str()
                .ok_or_else(|| GraphError::Malformed("variable missing name".into()))?
                .to_string();
            let resolved = resolve_variable(graph, asset_id, &var_name)?;
            graph.assets[asset_id].own_variables.insert(var_name, resolved);
        }
    }
    Ok(())
}

fn build_detectors(
    graph: &LanguageGraph,
    target_asset: AssetId,
    step_dict: &Value,
) -> Result<HashMap<String, LanguageGraphDetector>, GraphError> {
    let mut detectors = HashMap::new();
    let Some(dets) = step_dict.get("detectors").and_then(Value::as_object) else {
        return Ok(detectors);
    };
    for det in dets.values() {
        let mut context = HashMap::new();
        if let Some(ctx_obj) = det.get("context").and_then(Value::as_object) {
            for (label, ctx_expr) in ctx_obj {
                let (asset_type, expr_chain, attack_step_name) =
                    process_step_expression(graph, target_asset, None, ctx_expr)?;
                context.insert(
                    label.clone(),
                    LanguageGraphContextItem {
                        label: label.clone(),
                        asset_type,
                        attack_step_name,
                        expr: expr_chain,
                    },
                );
            }
        }
        let name = det.get("name").and_then(Value::as_str).map(str::to_string);
        let key = name.clone().unwrap_or_default();
        detectors.insert(
            key,
            LanguageGraphDetector {
                name,
                context,
                detector_type: det.get("type").and_then(Value::as_str).map(str::to_string),
                tprate: det.get("tprate").and_then(Value::as_f64),
                fprate: det.get("fprate").and_then(Value::as_f64),
            },
        );
    }
    Ok(detectors)
}

fn create_lg_attack_step_nodes(graph: &mut LanguageGraph) -> Result<HashMap<String, Value>, GraphError> {
    let mut attack_step_dicts = HashMap::new();
    let order = graph.asset_order.clone();

    for asset_id in order {
        let asset_name = graph.asset(asset_id).name.clone();
        let steps_spec = super::lookup::get_attacks_for_asset_type(&asset_name, &graph.lang_spec);

        for (step_name, step_dict) in steps_spec {
            let step_type = AttackStepType::parse(
                step_dict["type"]
                    .as_str()
                    .ok_or_else(|| GraphError::Malformed("attack step missing type".into()))?,
            )?;
            let causal_mode = step_dict["causal_mode"].as_str().and_then(CausalMode::parse);
            let ttc = if step_dict["ttc"].is_null() {
                None
            } else {
                Some(step_dict["ttc"].clone())
            };
            let overrides = step_dict
                .get("reaches")
                .filter(|r| !r.is_null())
                .and_then(|r| r.get("overrides"))
                .and_then(Value::as_bool)
                .unwrap_or(false);
            let tags = step_dict["tags"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|t| t.as_str().map(str::to_string))
                .collect();
            let detectors = build_detectors(graph, asset_id, &step_dict)?;

            let node = LanguageGraphAttackStep {
                name: step_name.clone(),
                step_type,
                asset: asset_id,
                causal_mode,
                ttc,
                overrides,
                own_children: HashMap::new(),
                own_parents: HashMap::new(),
                own_additive_model_effects: Vec::new(),
                own_subtractive_model_effects: Vec::new(),
                info: meta_map(&step_dict["meta"]),
                inherits: None,
                own_requires: Vec::new(),
                tags,
                detectors,
            };

            let full_name = format!("{asset_name}:{step_name}");
            let step_id = graph.steps.insert(node);
            graph.assets[asset_id].attack_steps.insert(step_name, step_id);
            attack_step_dicts.insert(full_name, step_dict);
        }
    }

    Ok(attack_step_dicts)
}

fn inherit_attack_steps(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let mut pending: VecDeque<AssetId> = graph.asset_order.iter().copied().collect();

    while let Some(asset_id) = pending.pop_front() {
        let Some(super_id) = graph.asset(asset_id).own_super_asset else {
            continue;
        };
        if pending.contains(&super_id) {
            pending.push_back(asset_id);
            continue;
        }

        let super_steps: Vec<(String, AttackStepId)> = graph
            .asset(super_id)
            .attack_steps
            .iter()
            .map(|(k, v)| (k.clone(), *v))
            .collect();

        for (step_name, super_step_id) in super_steps {
            let current_id = graph.asset(asset_id).attack_steps.get(&step_name).copied();

            match current_id {
                None => {
                    let super_step = graph.step(super_step_id).clone();
                    let node = LanguageGraphAttackStep {
                        name: super_step.name,
                        step_type: super_step.step_type,
                        asset: asset_id,
                        causal_mode: super_step.causal_mode,
                        ttc: super_step.ttc,
                        overrides: false,
                        own_children: HashMap::new(),
                        own_parents: HashMap::new(),
                        own_additive_model_effects: Vec::new(),
                        own_subtractive_model_effects: Vec::new(),
                        info: super_step.info,
                        inherits: Some(super_step_id),
                        own_requires: Vec::new(),
                        tags: super_step.tags,
                        detectors: HashMap::new(),
                    };
                    let new_id = graph.steps.insert(node);
                    graph.assets[asset_id].attack_steps.insert(step_name, new_id);
                }
                Some(current_id) => {
                    if graph.step(current_id).overrides {
                        continue;
                    }
                    let super_tags = graph.step(super_step_id).tags.clone();
                    let super_info = graph.step(super_step_id).info.clone();
                    let current = &mut graph.steps[current_id];
                    current.inherits = Some(super_step_id);
                    current.tags.extend(super_tags);
                    // Python's `info |= super_step.info` (dict union-assign):
                    // on key conflicts, the super asset's value wins.
                    for (k, v) in super_info {
                        current.info.insert(k, v);
                    }
                }
            }
        }
    }
    Ok(())
}

fn connect_attack_steps(
    graph: &mut LanguageGraph,
    attack_step_dicts: &HashMap<String, Value>,
) -> Result<(), GraphError> {
    for asset_id in graph.asset_order.clone() {
        let step_ids: Vec<AttackStepId> = graph.asset(asset_id).attack_steps.values().copied().collect();

        for step_id in step_ids {
            let full_name = graph.step(step_id).full_name(graph);
            let Some(step_dict) = attack_step_dicts.get(&full_name) else {
                continue;
            };
            let step_dict = step_dict.clone();
            let step_asset = graph.step(step_id).asset;

            if let Some(reaches) = step_dict.get("reaches").filter(|r| !r.is_null()) {
                let exprs = reaches["stepExpressions"].as_array().cloned().unwrap_or_default();
                for expr in exprs {
                    let (tgt_asset, chain, tgt_name) =
                        process_step_expression(graph, step_asset, None, &expr)?;
                    let Some(tgt_name) = tgt_name else {
                        return Err(GraphError::StepExpression(format!(
                            "Failed to find target attack step for:\n{}",
                            serde_json::to_string_pretty(&expr).unwrap_or_default()
                        )));
                    };
                    let tgt_step_id = *graph
                        .asset(tgt_asset)
                        .attack_steps
                        .get(&tgt_name)
                        .ok_or_else(|| {
                            GraphError::StepExpression(format!(
                                "Failed to find target attack step {tgt_name} on {}:\n{}",
                                graph.asset(tgt_asset).name,
                                serde_json::to_string_pretty(&expr).unwrap_or_default()
                            ))
                        })?;

                    let reverse_chain = reverse_expr_chain(chain.as_ref())?;
                    graph.steps[step_id]
                        .own_children
                        .entry(tgt_step_id)
                        .or_default()
                        .push(chain);
                    graph.steps[tgt_step_id]
                        .own_parents
                        .entry(step_id)
                        .or_default()
                        .push(reverse_chain);
                }
            }

            let step_type = graph.step(step_id).step_type;
            if matches!(step_type, AttackStepType::Exist | AttackStepType::NotExist) {
                let reqs = step_dict
                    .get("requires")
                    .filter(|r| !r.is_null())
                    .and_then(|r| r.get("stepExpressions"))
                    .and_then(Value::as_array)
                    .cloned()
                    .unwrap_or_default();
                if reqs.is_empty() {
                    return Err(GraphError::StepExpression(format!(
                        "Missing requirements for \"{}\" of type \"{}\":\n{}",
                        graph.step(step_id).name,
                        step_type.as_str(),
                        serde_json::to_string_pretty(&step_dict).unwrap_or_default()
                    )));
                }
                for expr in reqs {
                    let (_, chain, _) = process_step_expression(graph, step_asset, None, &expr)?;
                    let chain = chain.ok_or_else(|| {
                        GraphError::StepExpression(format!(
                            "Failed to find existence step requirement for:\n{expr}"
                        ))
                    })?;
                    graph.steps[step_id].own_requires.push(chain);
                }
            }
        }
    }
    Ok(())
}

fn connect_model_effects(
    graph: &mut LanguageGraph,
    attack_step_dicts: &HashMap<String, Value>,
) -> Result<(), GraphError> {
    for asset_id in graph.asset_order.clone() {
        let step_ids: Vec<AttackStepId> = graph.asset(asset_id).attack_steps.values().copied().collect();

        for step_id in step_ids {
            let full_name = graph.step(step_id).full_name(graph);
            let Some(step_dict) = attack_step_dicts.get(&full_name) else {
                continue;
            };
            let step_dict = step_dict.clone();
            let step_asset = graph.step(step_id).asset;

            if let Some(append_reaches) = step_dict.get("append_reaches").filter(|r| !r.is_null()) {
                let exprs = append_reaches["stepExpressions"].as_array().cloned().unwrap_or_default();
                for expr in exprs {
                    let model_effect = model_effect::build_model_effect(graph, step_asset, &expr, true)?;
                    graph.steps[step_id].own_additive_model_effects.push(model_effect);
                }
            }

            if let Some(remove_reaches) = step_dict.get("remove_reaches").filter(|r| !r.is_null()) {
                let exprs = remove_reaches["stepExpressions"].as_array().cloned().unwrap_or_default();
                for expr in exprs {
                    let model_effect = model_effect::build_model_effect(graph, step_asset, &expr, false)?;
                    graph.steps[step_id].own_subtractive_model_effects.push(model_effect);
                }
            }
        }
    }
    Ok(())
}

fn generate_attack_steps(graph: &mut LanguageGraph) -> Result<(), GraphError> {
    let attack_step_dicts = create_lg_attack_step_nodes(graph)?;
    inherit_attack_steps(graph)?;
    connect_attack_steps(graph, &attack_step_dicts)?;
    connect_model_effects(graph, &attack_step_dicts)?;
    assoc_traversal::validate_model_effects(graph)?;
    Ok(())
}
