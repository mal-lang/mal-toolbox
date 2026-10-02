//! Port of `maltoolbox/language/step_expression_processor.py`.

use serde_json::Value;

use super::expr_chain::{ExprType, ExpressionsChain};
use super::ids::AssetId;
use super::lookup::get_var_expr_for_asset;
use super::{GraphError, LanguageGraph};

/// (target asset, resulting associations chain, attack step name) -
/// mirrors Python's `StepResult` triplet.
pub type StepResult = (AssetId, Option<ExpressionsChain>, Option<String>);

pub fn process_attack_step_expression(target_asset: AssetId, step_expression: &Value) -> StepResult {
    let name = step_expression["name"].as_str().map(str::to_string);
    (target_asset, None, name)
}

pub fn process_set_operation_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let (lh_target_asset, lh_expr_chain, _) =
        process_step_expression(graph, target_asset, expr_chain, &step_expression["lhs"])?;
    let (rh_target_asset, rh_expr_chain, _) =
        process_step_expression(graph, target_asset, expr_chain, &step_expression["rhs"])?;

    if graph
        .get_all_common_superassets(lh_target_asset, rh_target_asset)
        .is_empty()
    {
        return Err(GraphError::Malformed(format!(
            "Set operation attempted between targets that do not share any common superassets: {} and {}!",
            graph.asset(lh_target_asset).name,
            graph.asset(rh_target_asset).name,
        )));
    }

    let op = match step_expression["type"].as_str() {
        Some("union") => ExprType::Union,
        Some("intersection") => ExprType::Intersection,
        Some("difference") => ExprType::Difference,
        other => {
            return Err(GraphError::Malformed(format!(
                "unknown set operation type: {other:?}"
            )))
        }
    };

    let new_chain = ExpressionsChain::Binary {
        op,
        left: lh_expr_chain.map(Box::new),
        right: rh_expr_chain.map(Box::new),
    };
    Ok((lh_target_asset, Some(new_chain), None))
}

pub fn process_variable_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let var_name = step_expression["name"]
        .as_str()
        .ok_or_else(|| GraphError::Malformed("variable step expression missing name".into()))?;

    let (var_target_asset, var_expr_chain) = resolve_variable(graph, target_asset, var_name)?;

    if var_expr_chain.is_none() {
        return Err(GraphError::Lookup(format!(
            "Failed to find variable \"{var_name}\" for {}",
            graph.asset(target_asset).name
        )));
    }

    Ok((var_target_asset, var_expr_chain, None))
}

pub fn process_field_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let fieldname = step_expression["name"]
        .as_str()
        .ok_or_else(|| GraphError::Malformed("field step expression missing name".into()))?;

    for association in graph.associations(target_asset).values() {
        if association.left_field.fieldname == fieldname
            && graph.is_subasset_of(target_asset, association.right_field.asset)
        {
            return Ok((
                association.left_field.asset,
                Some(ExpressionsChain::Field {
                    association: association.clone(),
                    fieldname: fieldname.to_string(),
                }),
                None,
            ));
        }
        if association.right_field.fieldname == fieldname
            && graph.is_subasset_of(target_asset, association.left_field.asset)
        {
            return Ok((
                association.right_field.asset,
                Some(ExpressionsChain::Field {
                    association: association.clone(),
                    fieldname: fieldname.to_string(),
                }),
                None,
            ));
        }
    }

    if fieldname == "self" {
        return Ok((target_asset, None, None));
    }

    Err(GraphError::Lookup(format!(
        "Failed to find field {fieldname} on asset {}!",
        graph.asset(target_asset).name
    )))
}

pub fn process_transitive_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let (result_target_asset, result_expr_chain, _) = process_step_expression(
        graph,
        target_asset,
        expr_chain,
        &step_expression["stepExpression"],
    )?;
    let new_chain = ExpressionsChain::Transitive {
        sub: Box::new(result_expr_chain.ok_or_else(|| {
            GraphError::Malformed("TRANSITIVE requires sub_link".into())
        })?),
    };
    Ok((result_target_asset, Some(new_chain), None))
}

pub fn process_sub_type_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let subtype_name = step_expression["subType"]
        .as_str()
        .ok_or_else(|| GraphError::Malformed("subType step expression missing subType".into()))?;
    let (result_target_asset, result_expr_chain, _) = process_step_expression(
        graph,
        target_asset,
        expr_chain,
        &step_expression["stepExpression"],
    )?;

    let subtype_asset = graph.asset_id(subtype_name).ok_or_else(|| {
        GraphError::Malformed(format!("Failed to find subtype {subtype_name}"))
    })?;

    if !graph.is_subasset_of(subtype_asset, result_target_asset) {
        return Err(GraphError::Malformed(format!(
            "Found subtype {subtype_name} which does not extend {}, subtype cannot be resolved.",
            graph.asset(result_target_asset).name
        )));
    }

    let new_chain = ExpressionsChain::SubType {
        sub: Box::new(result_expr_chain.ok_or_else(|| {
            GraphError::Malformed("SUBTYPE requires sub_link".into())
        })?),
        subtype: subtype_asset,
    };
    Ok((subtype_asset, Some(new_chain), None))
}

pub fn process_multiplicity_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let multiplicity = step_expression["multiplicity"].clone();
    let (result_target_asset, result_expr_chain, step_name) = process_step_expression(
        graph,
        target_asset,
        expr_chain,
        &step_expression["stepExpression"],
    )?;

    if let Some(step_name) = step_name {
        return Err(GraphError::Malformed(format!(
            "Step `{step_name}` cannot have a multiplicity qualifier."
        )));
    }

    let new_chain = ExpressionsChain::Multiplicity {
        sub: Box::new(result_expr_chain.ok_or_else(|| {
            GraphError::Malformed("MULTIPLICITY requires sub_link".into())
        })?),
        multiplicity,
    };
    Ok((result_target_asset, Some(new_chain), None))
}

pub fn process_collect_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let (lh_target_asset, lh_expr_chain, _) =
        process_step_expression(graph, target_asset, expr_chain, &step_expression["lhs"])?;

    let (rh_target_asset, rh_expr_chain, rh_attack_step_name) =
        process_step_expression(graph, lh_target_asset, None, &step_expression["rhs"])?;

    let new_expr_chain = match rh_expr_chain {
        Some(rh) => Some(ExpressionsChain::Binary {
            op: ExprType::Collect,
            left: lh_expr_chain.map(Box::new),
            right: Some(Box::new(rh)),
        }),
        None => lh_expr_chain,
    };

    Ok((rh_target_asset, new_expr_chain, rh_attack_step_name))
}

pub fn process_assoc_op_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    let (result_target_asset, result_expr_chain, result_step_name) =
        process_step_expression(graph, target_asset, expr_chain, &step_expression["operand"])?;

    if result_step_name.is_some() {
        return Err(GraphError::Malformed(
            "ASSOC_OP can not have an attack step as operand".into(),
        ));
    }

    let new_chain = ExpressionsChain::AssocOp {
        sub: Box::new(result_expr_chain.ok_or_else(|| {
            GraphError::Malformed("ASSOC_OP requires sub_link".into())
        })?),
    };
    Ok((result_target_asset, Some(new_chain), None))
}

pub fn process_step_expression(
    graph: &LanguageGraph,
    target_asset: AssetId,
    expr_chain: Option<&ExpressionsChain>,
    step_expression: &Value,
) -> Result<StepResult, GraphError> {
    match step_expression["type"].as_str() {
        Some("attackStep") => Ok(process_attack_step_expression(target_asset, step_expression)),
        Some("union") | Some("intersection") | Some("difference") => {
            process_set_operation_step_expression(graph, target_asset, expr_chain, step_expression)
        }
        Some("variable") => process_variable_step_expression(graph, target_asset, step_expression),
        Some("field") => process_field_step_expression(graph, target_asset, step_expression),
        Some("transitive") => {
            process_transitive_step_expression(graph, target_asset, expr_chain, step_expression)
        }
        Some("subType") => {
            process_sub_type_step_expression(graph, target_asset, expr_chain, step_expression)
        }
        Some("multiplicity") => {
            process_multiplicity_step_expression(graph, target_asset, expr_chain, step_expression)
        }
        Some("collect") => {
            process_collect_step_expression(graph, target_asset, expr_chain, step_expression)
        }
        other => Err(GraphError::Lookup(format!(
            "Unknown attack step type: {other:?}"
        ))),
    }
}

/// Port of `reverse_expr_chain`. The Python original threads a
/// `reverse_chain` accumulator parameter through the recursion, but every
/// call site passes `None` for it and no branch ever assigns anything
/// else into it - it only ever surfaces, unchanged, as the result of the
/// `if not expr_chain: return reverse_chain` base case. Since it is
/// therefore always `None` in practice, this port drops the dead
/// parameter rather than threading a value that can never be anything
/// else.
pub fn reverse_expr_chain(
    expr_chain: Option<&ExpressionsChain>,
) -> Result<Option<ExpressionsChain>, GraphError> {
    let Some(chain) = expr_chain else {
        return Ok(None);
    };

    match chain {
        ExpressionsChain::Binary { op, left, right } => {
            let left_reverse = reverse_expr_chain(left.as_deref())?;
            let right_reverse = reverse_expr_chain(right.as_deref())?;
            let new_chain = if *op == ExprType::Collect {
                ExpressionsChain::Binary {
                    op: *op,
                    left: right_reverse.map(Box::new),
                    right: left_reverse.map(Box::new),
                }
            } else {
                ExpressionsChain::Binary {
                    op: *op,
                    left: left_reverse.map(Box::new),
                    right: right_reverse.map(Box::new),
                }
            };
            Ok(Some(new_chain))
        }
        ExpressionsChain::Transitive { sub } => {
            let result = reverse_expr_chain(Some(sub))?;
            Ok(Some(ExpressionsChain::Transitive {
                sub: Box::new(result.ok_or_else(|| {
                    GraphError::Malformed("TRANSITIVE requires sub_link".into())
                })?),
            }))
        }
        ExpressionsChain::Field {
            association,
            fieldname,
        } => {
            let opposite = association.get_opposite_fieldname(fieldname)?;
            Ok(Some(ExpressionsChain::Field {
                association: association.clone(),
                fieldname: opposite,
            }))
        }
        ExpressionsChain::SubType { sub, subtype } => {
            let result = reverse_expr_chain(Some(sub))?;
            Ok(Some(ExpressionsChain::SubType {
                sub: Box::new(result.ok_or_else(|| {
                    GraphError::Malformed("SUBTYPE requires sub_link".into())
                })?),
                subtype: *subtype,
            }))
        }
        other => Err(GraphError::Malformed(format!(
            "Unknown assoc chain element \"{:?}\"",
            other.expr_type()
        ))),
    }
}

pub fn resolve_variable(
    graph: &LanguageGraph,
    asset: AssetId,
    var_name: &str,
) -> Result<(AssetId, Option<ExpressionsChain>), GraphError> {
    let vars = graph.variables(asset);
    if let Some((target, chain)) = vars.get(var_name) {
        return Ok((*target, chain.clone()));
    }

    let var_expr = get_var_expr_for_asset(&graph.asset(asset).name.clone(), var_name, &graph.lang_spec)?;
    let (target_asset, expr_chain, _) = process_step_expression(graph, asset, None, &var_expr)?;
    Ok((target_asset, expr_chain))
}
