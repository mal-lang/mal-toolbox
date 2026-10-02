//! Port of `maltoolbox/language/assoc_traversal_processor.py`.
//!
//! Resolves [`super::model_effect::AssocTraversalChain`]s against an
//! actual language graph - walking associations from a starting set of
//! assets - and validates every `LanguageGraphModelEffect` built by
//! [`super::model_effect::build_model_effect`].

use std::collections::HashSet;

use super::ids::{AssetId, AttackStepId};
use super::model_effect::{
    AssocSet, AssocTraversal, AssocTraversalElem, GlobAssocTraversal, ModelEffectType, SetOperation,
};
use super::{GraphError, LanguageGraph};

fn assoc_traversal(
    graph: &LanguageGraph,
    step: AttackStepId,
    instigating_assets: &HashSet<AssetId>,
    traversal: &AssocTraversal,
) -> Result<HashSet<AssetId>, GraphError> {
    let mut next_assets = HashSet::new();
    for &asset in instigating_assets {
        if traversal.field_name == "self" {
            next_assets.insert(graph.step(step).asset);
            continue;
        }
        let associations = graph.associations(asset);
        let assoc = associations.get(&traversal.field_name).ok_or_else(|| {
            GraphError::Malformed(format!(
                "Asset {} does not have an association for field {}.",
                graph.asset(asset).name,
                traversal.field_name
            ))
        })?;
        next_assets.insert(assoc.get_field(&traversal.field_name).asset);
    }
    Ok(next_assets)
}

/// Port of `_glob_assoc_traversal` *as written*, not as apparently
/// intended: both the initial `next_assets` and every loop iteration's
/// `new_assets` are recomputed from the same unchanging
/// `instigating_assets`, never from the growing result - so despite the
/// while-loop shape (which reads like it's building a transitive
/// closure, matching the `*` operator it implements), this always
/// resolves to exactly one application of `pattern`. Confirmed against
/// the Python oracle, not just by reading the source. This is very
/// likely an upstream bug worth reporting (the user co-maintains
/// mal-toolbox) - ported bug-for-bug per this project's behavior-
/// compatibility mandate rather than "fixed" into a real transitive
/// closure, which would change what `X.field*` resolves to relative to
/// the real implementation.
fn glob_assoc_traversal(
    graph: &LanguageGraph,
    step: AttackStepId,
    instigating_assets: &HashSet<AssetId>,
    glob: &GlobAssocTraversal,
) -> Result<HashSet<AssetId>, GraphError> {
    traverse_association_chain(graph, step, instigating_assets, &glob.pattern)
}

fn assoc_set_traversal(
    graph: &LanguageGraph,
    step: AttackStepId,
    starting_assets: &HashSet<AssetId>,
    assoc_set: &AssocSet,
) -> Result<HashSet<AssetId>, GraphError> {
    let left = traverse_association_chain(graph, step, starting_assets, &assoc_set.left)?;
    let right = traverse_association_chain(graph, step, starting_assets, &assoc_set.right)?;
    Ok(match assoc_set.set_op {
        SetOperation::Union => left.union(&right).copied().collect(),
        SetOperation::Difference => left.difference(&right).copied().collect(),
        SetOperation::Intersection => left.intersection(&right).copied().collect(),
    })
}

fn traverse_association_chain(
    graph: &LanguageGraph,
    step: AttackStepId,
    instigating_assets: &HashSet<AssetId>,
    chain: &[AssocTraversalElem],
) -> Result<HashSet<AssetId>, GraphError> {
    let mut current = instigating_assets.clone();
    for elem in chain {
        current = match elem {
            AssocTraversalElem::Traversal(t) => assoc_traversal(graph, step, &current, t)?,
            AssocTraversalElem::Glob(g) => glob_assoc_traversal(graph, step, &current, g)?,
            AssocTraversalElem::Set(s) => assoc_set_traversal(graph, step, &current, s)?,
        };
    }
    Ok(current)
}

/// (anchor asset, field name used to reach the terminal, terminal asset).
pub type TerminalResolve = (AssetId, String, AssetId);

fn resolve_terminal_traversal(
    graph: &LanguageGraph,
    step: AttackStepId,
    instigating_assets: &HashSet<AssetId>,
    chain: &[AssocTraversalElem],
) -> Result<HashSet<TerminalResolve>, GraphError> {
    let split = chain.len().saturating_sub(1);
    let (init, last_slice) = chain.split_at(split);
    let current_assets = traverse_association_chain(graph, step, instigating_assets, init)?;
    let last = last_slice
        .first()
        .ok_or_else(|| GraphError::Malformed("empty association traversal chain".into()))?;

    match last {
        AssocTraversalElem::Traversal(t) => {
            let mut result = HashSet::new();
            for &asset in &current_assets {
                if t.field_name == "self" {
                    result.insert((asset, t.field_name.clone(), graph.step(step).asset));
                    continue;
                }
                let candidate = if let Some(filter) = t.asset_filter {
                    filter
                } else {
                    let associations = graph.associations(asset);
                    let assoc = associations.get(&t.field_name).ok_or_else(|| {
                        GraphError::Malformed(format!(
                            "Asset {} does not have an association for field {}.",
                            graph.asset(asset).name,
                            t.field_name
                        ))
                    })?;
                    assoc.get_field(&t.field_name).asset
                };
                result.insert((asset, t.field_name.clone(), candidate));
            }
            Ok(result)
        }
        // `*` is a repeated application of the pattern, so the
        // termination is whatever the pattern itself terminates in.
        AssocTraversalElem::Glob(g) => {
            resolve_terminal_traversal(graph, step, &current_assets, &g.pattern)
        }
        AssocTraversalElem::Set(s) => {
            let left = resolve_terminal_traversal(graph, step, &current_assets, &s.left)?;
            let right = resolve_terminal_traversal(graph, step, &current_assets, &s.right)?;
            Ok(match s.set_op {
                SetOperation::Union => left.union(&right).cloned().collect(),
                SetOperation::Difference => left.difference(&right).cloned().collect(),
                SetOperation::Intersection => left.intersection(&right).cloned().collect(),
            })
        }
    }
}

/// Port of `validate_model_effects`.
pub fn validate_model_effects(graph: &LanguageGraph) -> Result<(), GraphError> {
    for &asset_id in &graph.asset_order {
        let step_ids: Vec<AttackStepId> = graph.asset(asset_id).attack_steps.values().copied().collect();
        for step_id in step_ids {
            let step = graph.step(step_id);
            let mut effects = step.additive_model_effects(graph);
            effects.extend(step.subtractive_model_effects(graph));

            for model_effect in &effects {
                let base_resolves = resolve_terminal_traversal(
                    graph,
                    step_id,
                    &HashSet::from([asset_id]),
                    &model_effect.base,
                )?;

                for (target_index, dyn_target) in model_effect.targets.iter().enumerate() {
                    let is_edge_addition =
                        model_effect.model_effect_type == ModelEffectType::Additive && dyn_target.assoc_op;

                    if is_edge_addition {
                        let dyn_target_resolves = resolve_terminal_traversal(
                            graph,
                            step_id,
                            &HashSet::from([asset_id]),
                            &dyn_target.assoc_traversal,
                        )?;
                        for &(_, _, terminating_asset) in &dyn_target_resolves {
                            for &(_, ref base_field_name, base_terminating_asset) in &base_resolves {
                                if !graph.is_subasset_of(base_terminating_asset, terminating_asset) {
                                    return Err(GraphError::Malformed(format!(
                                        "Invalid model effect for edge addition. Base terminates in field {base_field_name} with type {}, which is not a subasset of the target asset {} that terminates the dynamic target with index {target_index}, in {}.",
                                        graph.asset(base_terminating_asset).name,
                                        graph.asset(terminating_asset).name,
                                        step.full_name(graph),
                                    )));
                                }
                            }
                        }
                    } else {
                        let base_terminals: HashSet<AssetId> =
                            base_resolves.iter().map(|r| r.2).collect();
                        resolve_terminal_traversal(graph, step_id, &base_terminals, &dyn_target.assoc_traversal)?;
                    }
                }
            }
        }
    }
    Ok(())
}
