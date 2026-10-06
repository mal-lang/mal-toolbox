//! Port of `maltoolbox/language/language_graph_lookup.py`.

use indexmap::IndexMap;
use serde_json::Value;

use super::GraphError;

fn find_asset<'a>(lang_spec: &'a Value, asset_type: &str) -> Option<&'a Value> {
    lang_spec["assets"]
        .as_array()?
        .iter()
        .find(|a| a["name"].as_str() == Some(asset_type))
}

/// Attack step dicts for `asset_type`, keyed by step name.
///
/// Must preserve the declaration order of `attackSteps` in the language
/// spec (matches the pure-Python original's `{step['name']: step for step
/// in asset['attackSteps']}` dict comprehension, which preserves insertion
/// order) - this order determines attack-step/node-id assignment order
/// downstream, so a `HashMap` here would make graph generation
/// nondeterministic.
pub fn get_attacks_for_asset_type(asset_type: &str, lang_spec: &Value) -> IndexMap<String, Value> {
    let Some(asset) = find_asset(lang_spec, asset_type) else {
        return IndexMap::new();
    };
    asset["attackSteps"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|step| {
            step["name"]
                .as_str()
                .map(|name| (name.to_string(), step.clone()))
        })
        .collect()
}

/// Variable entry dicts (`{name, stepExpression}`) for `asset_type`.
pub fn get_variables_for_asset_type(
    asset_type: &str,
    lang_spec: &Value,
) -> Result<Vec<Value>, GraphError> {
    let asset = find_asset(lang_spec, asset_type).ok_or_else(|| {
        GraphError::Lookup(format!(
            "Failed to find asset type {asset_type} in language specification when looking for variables."
        ))
    })?;
    Ok(asset["variables"].as_array().cloned().unwrap_or_default())
}

/// The `stepExpression` dict for a specific variable on `asset_type`.
pub fn get_var_expr_for_asset(
    asset_type: &str,
    var_name: &str,
    lang_spec: &Value,
) -> Result<Value, GraphError> {
    let vars = get_variables_for_asset_type(asset_type, lang_spec)?;
    vars.iter()
        .find(|v| v["name"].as_str() == Some(var_name))
        .map(|v| v["stepExpression"].clone())
        .ok_or_else(|| {
            GraphError::Lookup(format!(
                "Failed to find variable name \"{var_name}\" in language specification when looking for variables for \"{asset_type}\" asset."
            ))
        })
}
