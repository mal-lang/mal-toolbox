//! Port of `maltoolbox/language/compiler/mal_analyzer.py`'s semantic
//! validation, including its two purely-cosmetic warnings (abstract-
//! asset-never-extended, duplicate-CIA-classification), which have no
//! effect on compilation success or on any serialized output but are
//! still useful diagnostics for language authors. Printed to stderr with
//! `eprintln!` rather than routed through a logging framework, since no
//! logging subsystem is ported in this project (see `PORTING_NOTES.md`
//! §8). The abstract-asset check lives here, over the compiled langspec;
//! the duplicate-CIA check lives in `visit_cias` in the sibling
//! `compiler` module instead, since by the time a langspec reaches this
//! pass its `risk` flags are already deduplicated booleans - the raw,
//! possibly-repeated CIA letters only exist during that earlier walk.
//!
//! Unlike the Python original - a stateful visitor hooked into the same
//! tree-sitter walk the compiler performs, accumulating state incrementally
//! node-by-node - this operates as a single pass over the already-built
//! `langspec` [`Value`], re-deriving the inheritance-aware step/field/
//! variable resolution Python's incrementally-built dicts provided for
//! free. Diagnostic text intentionally drops tree-sitter line numbers
//! (wire compatibility covers the serialized Model/LanguageGraph/
//! AttackGraph schema, not diagnostic strings), but otherwise mirrors the
//! original's checks and their relative error precedence.

use std::collections::{HashMap, HashSet};

use serde_json::Value;

use super::distributions;
use super::CompileError;

fn err(msg: impl Into<String>) -> CompileError {
    CompileError::Semantic(msg.into())
}

/// `asset -> field_name -> target asset name`, the flattened (own +
/// inherited) association fields available on an asset. Port of
/// `_analyse_fields`/`_add_field`'s `self._associations`.
type FieldMap = HashMap<String, HashMap<String, String>>;
/// `asset -> variable_name -> raw stepExpression`, flattened (own +
/// inherited, pre-resolution). Port of `self._vars`.
type RawVarMap = HashMap<String, HashMap<String, Value>>;
/// `asset -> attack step names`, flattened (own + inherited). Port of
/// `self._steps`'s keys (values aren't needed downstream - only whether a
/// name resolves).
type StepMap = HashMap<String, HashSet<String>>;

struct Ctx<'a> {
    assets_by_name: HashMap<&'a str, &'a Value>,
    fields: FieldMap,
    raw_vars: RawVarMap,
    steps: StepMap,
}

pub fn analyze(langspec: &Value) -> Result<(), CompileError> {
    let assets: &[Value] = langspec["assets"].as_array().map(Vec::as_slice).unwrap_or(&[]);
    let associations: &[Value] = langspec["associations"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[]);

    check_duplicate_assets(assets)?;
    check_duplicate_steps_and_vars(assets)?;
    check_cia_and_ttc(assets)?;

    analyse_defines(langspec)?;
    analyse_extends(assets)?;
    analyse_parents(assets)?;
    warn_abstract_never_extended(assets);
    analyse_association(associations, assets)?;

    let assets_by_name: HashMap<&str, &Value> = assets
        .iter()
        .filter_map(|a| a["name"].as_str().map(|n| (n, a)))
        .collect();

    let steps = analyse_steps(assets, &assets_by_name)?;
    let fields = analyse_fields(assets, &assets_by_name, associations, &steps)?;
    let raw_vars = analyse_variables(assets, &assets_by_name)?;

    let ctx = Ctx {
        assets_by_name,
        fields,
        raw_vars,
        steps,
    };

    validate_variables_resolve(&ctx)?;
    analyse_reaches(&ctx, assets)?;

    Ok(())
}

// ---------------------------------------------------------------------
// duplicate-name checks (the Python original's incremental check_* hooks)
// ---------------------------------------------------------------------

fn check_duplicate_assets(assets: &[Value]) -> Result<(), CompileError> {
    let mut seen = HashSet::new();
    for asset in assets {
        let name = asset["name"].as_str().unwrap_or_default();
        if !seen.insert(name) {
            return Err(err(format!("Asset '{name}' previously defined")));
        }
    }
    Ok(())
}

fn check_duplicate_steps_and_vars(assets: &[Value]) -> Result<(), CompileError> {
    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();

        let mut seen_steps = HashSet::new();
        for step in asset["attackSteps"].as_array().into_iter().flatten() {
            let step_name = step["name"].as_str().unwrap_or_default();
            if !seen_steps.insert(step_name) {
                return Err(err(format!(
                    "Attack step '{step_name}' previously defined in asset '{asset_name}'"
                )));
            }
        }

        let mut seen_vars = HashSet::new();
        for var in asset["variables"].as_array().into_iter().flatten() {
            let var_name = var["name"].as_str().unwrap_or_default();
            if !seen_vars.insert(var_name) {
                return Err(err(format!(
                    "Variable '{var_name}' previously defined in asset '{asset_name}'"
                )));
            }
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------
// defines
// ---------------------------------------------------------------------

fn analyse_defines(langspec: &Value) -> Result<(), CompileError> {
    let defines = &langspec["defines"];

    match defines.get("id").and_then(Value::as_str) {
        Some(id) if id.is_empty() => return Err(err("Define 'id' cannot be empty")),
        Some(_) => {}
        None => return Err(err("Missing required define '#id: \"\"'")),
    }

    match defines.get("version").and_then(Value::as_str) {
        Some(version) if !is_semver_prefix(version) => {
            return Err(err(
                "Define 'version' must be valid semantic versioning without pre-release identifier and build metadata",
            ))
        }
        Some(_) => {}
        None => return Err(err("Missing required define '#version: \"\"'")),
    }

    Ok(())
}

/// Port of Python's `re.match(r'\d+\.\d+\.\d+', version)` - a *prefix*
/// match, not a full-string one.
fn is_semver_prefix(version: &str) -> bool {
    let mut parts = version.split('.');
    let is_digits = |s: Option<&str>| s.map(|p| !p.is_empty() && p.chars().all(|c| c.is_ascii_digit())).unwrap_or(false);
    is_digits(parts.next()) && is_digits(parts.next()) && parts.next().map(|p| {
        let digits: String = p.chars().take_while(|c| c.is_ascii_digit()).collect();
        !digits.is_empty()
    }).unwrap_or(false)
}

// ---------------------------------------------------------------------
// extends / parents
// ---------------------------------------------------------------------

fn analyse_extends(assets: &[Value]) -> Result<(), CompileError> {
    let names: HashSet<&str> = assets.iter().filter_map(|a| a["name"].as_str()).collect();
    for asset in assets {
        if let Some(super_asset) = asset["superAsset"].as_str() {
            if !names.contains(super_asset) {
                return Err(err(format!("Asset '{super_asset}' not defined")));
            }
        }
    }
    Ok(())
}

/// Port of `_analyse_abstract`'s warning: an abstract asset that no other
/// asset extends is almost certainly dead weight in the language, but
/// it's not an error - just worth flagging.
fn warn_abstract_never_extended(assets: &[Value]) {
    for asset in assets {
        if asset["isAbstract"].as_bool() != Some(true) {
            continue;
        }
        let Some(name) = asset["name"].as_str() else {
            continue;
        };
        let extended = assets
            .iter()
            .any(|a| a["superAsset"].as_str() == Some(name));
        if !extended {
            eprintln!("warning: asset '{name}' is abstract but never extended to");
        }
    }
}

fn analyse_parents(assets: &[Value]) -> Result<(), CompileError> {
    let by_name: HashMap<&str, &Value> = assets
        .iter()
        .filter_map(|a| a["name"].as_str().map(|n| (n, a)))
        .collect();

    for asset in assets {
        let name = asset["name"].as_str().unwrap_or_default();
        let mut parents: Vec<String> = Vec::new();
        let mut current = Some(name.to_string());
        while let Some(cur) = current {
            if parents.contains(&cur) {
                let chain = format!("{} -> {cur}", parents.join(" -> "));
                return Err(err(format!("Asset '{cur}' extends in loop '{chain}'")));
            }
            parents.push(cur.clone());
            current = by_name
                .get(cur.as_str())
                .and_then(|a| a["superAsset"].as_str())
                .map(String::from);
        }
    }
    Ok(())
}

/// Port of `_get_parents`: an asset's ancestor chain, root-first, ending
/// with the asset itself. Assumes `analyse_parents` already ran (no
/// cycle-checking here, only a defensive break mirroring the original).
fn get_parents(assets_by_name: &HashMap<&str, &Value>, asset_name: &str) -> Vec<String> {
    let mut parents = vec![asset_name.to_string()];
    let mut current = asset_name.to_string();
    loop {
        let Some(super_asset) = assets_by_name
            .get(current.as_str())
            .and_then(|a| a["superAsset"].as_str())
        else {
            break;
        };
        if parents.iter().any(|p| p == super_asset) {
            break;
        }
        parents.insert(0, super_asset.to_string());
        current = super_asset.to_string();
    }
    parents
}

fn is_child(assets_by_name: &HashMap<&str, &Value>, parent_name: &str, child_name: &str) -> bool {
    if parent_name == child_name {
        return true;
    }
    let mut current = child_name.to_string();
    loop {
        let Some(super_asset) = assets_by_name
            .get(current.as_str())
            .and_then(|a| a["superAsset"].as_str())
        else {
            return false;
        };
        if super_asset == parent_name {
            return true;
        }
        current = super_asset.to_string();
    }
}

fn get_lca(assets_by_name: &HashMap<&str, &Value>, a: &str, b: &str) -> Option<String> {
    if is_child(assets_by_name, a, b) {
        return Some(a.to_string());
    }
    if is_child(assets_by_name, b, a) {
        return Some(b.to_string());
    }
    let a_parent = assets_by_name.get(a)?["superAsset"].as_str()?;
    let b_parent = assets_by_name.get(b)?["superAsset"].as_str()?;
    get_lca(assets_by_name, a_parent, b_parent)
}

// ---------------------------------------------------------------------
// associations
// ---------------------------------------------------------------------

fn analyse_association(associations: &[Value], assets: &[Value]) -> Result<(), CompileError> {
    let names: HashSet<&str> = assets.iter().filter_map(|a| a["name"].as_str()).collect();
    for assoc in associations {
        let left = assoc["leftAsset"].as_str().unwrap_or_default();
        let right = assoc["rightAsset"].as_str().unwrap_or_default();
        if !names.contains(left) {
            return Err(err(format!("Left asset '{left}' is not defined")));
        }
        if !names.contains(right) {
            return Err(err(format!("Right asset '{left}' is not defined")));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------
// steps (inheritance-aware override/type-consistency validation)
// ---------------------------------------------------------------------

/// Whether an attack step's `reaches` operator is an override form
/// (`->`/`A>`/`R>`) rather than an append form (`+>`/`+A>`/`+R>`), or the
/// step has no reaches clause at all (vacuously fine to be a first
/// definition). Port of `_read_steps`'s inline operator check - note it
/// only ever looks at whichever single reaches-like clause is present,
/// mirroring `attackStep_node.child_by_field_name('reaches')` matching
/// any of `reaching`/`append_reaching`/`remove_reaching`.
fn step_overrides_or_absent(step: &Value) -> bool {
    for key in ["reaches", "append_reaches", "remove_reaches"] {
        let clause = &step[key];
        if !clause.is_null() {
            return clause["overrides"].as_bool().unwrap_or(false);
        }
    }
    true
}

fn analyse_steps(
    assets: &[Value],
    assets_by_name: &HashMap<&str, &Value>,
) -> Result<StepMap, CompileError> {
    let mut resolved: StepMap = HashMap::new();

    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();
        let chain = get_parents(assets_by_name, asset_name);

        let mut first_type: HashMap<String, String> = HashMap::new();
        let mut names: HashSet<String> = HashSet::new();

        for level in &chain {
            let Some(level_asset) = assets_by_name.get(level.as_str()) else {
                continue;
            };
            for step in level_asset["attackSteps"].as_array().into_iter().flatten() {
                let step_name = step["name"].as_str().unwrap_or_default().to_string();
                let step_type = step["type"].as_str().unwrap_or_default().to_string();

                match first_type.get(&step_name) {
                    None => {
                        if !step_overrides_or_absent(step) {
                            return Err(err(format!(
                                "Cannot inherit attack step '{step_name}' without previous definition"
                            )));
                        }
                        first_type.insert(step_name.clone(), step_type);
                        names.insert(step_name);
                    }
                    Some(prev_type) => {
                        if *prev_type != step_type {
                            return Err(err(format!(
                                "Cannot override attack step '{step_name}' previously defined with different type '{step_type}' =/= '{prev_type}'"
                            )));
                        }
                        names.insert(step_name);
                    }
                }
            }
        }

        resolved.insert(asset_name.to_string(), names);
    }

    Ok(resolved)
}

// ---------------------------------------------------------------------
// fields (association field flattening down the hierarchy)
// ---------------------------------------------------------------------

fn analyse_fields(
    assets: &[Value],
    assets_by_name: &HashMap<&str, &Value>,
    associations: &[Value],
    steps: &StepMap,
) -> Result<FieldMap, CompileError> {
    let mut fields: FieldMap = HashMap::new();

    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();
        let parents = get_parents(assets_by_name, asset_name);

        for parent in &parents {
            for assoc in associations {
                let left_asset = assoc["leftAsset"].as_str().unwrap_or_default();
                let right_asset = assoc["rightAsset"].as_str().unwrap_or_default();

                if left_asset == parent {
                    let right_field = assoc["rightField"].as_str().unwrap_or_default();
                    add_field(&mut fields, steps, parent, asset_name, right_field, right_asset)?;
                }
                if right_asset == parent {
                    let left_field = assoc["leftField"].as_str().unwrap_or_default();
                    add_field(&mut fields, steps, parent, asset_name, left_field, left_asset)?;
                }
            }
        }
    }

    Ok(fields)
}

fn add_field(
    fields: &mut FieldMap,
    steps: &StepMap,
    parent: &str,
    asset: &str,
    field: &str,
    target_asset: &str,
) -> Result<(), CompileError> {
    if fields.get(asset).map(|m| m.contains_key(field)).unwrap_or(false) {
        return Err(err(format!("Field {parent}.{field} previously defined")));
    }
    if steps.get(asset).map(|s| s.contains(field)).unwrap_or(false) {
        return Err(err(format!(
            "Field {field} previously defined as an attack step"
        )));
    }
    fields
        .entry(asset.to_string())
        .or_default()
        .insert(field.to_string(), target_asset.to_string());
    Ok(())
}

// ---------------------------------------------------------------------
// variables
// ---------------------------------------------------------------------

fn own_vars_of(asset: &Value) -> HashMap<String, Value> {
    asset["variables"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(|v| Some((v["name"].as_str()?.to_string(), v["stepExpression"].clone())))
        .collect()
}

/// Port of `_analyse_variables`'s hierarchy-flattening half: for every
/// asset, merges its own variables with every ancestor's own variables,
/// raising if the SAME name is independently declared (not merely
/// inherited) at more than one level in the chain - this holds even if
/// the two declarations are identical, since Python's check compares AST
/// node identity, never content.
fn analyse_variables(
    assets: &[Value],
    assets_by_name: &HashMap<&str, &Value>,
) -> Result<RawVarMap, CompileError> {
    let mut resolved: RawVarMap = HashMap::new();

    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();
        let mut chain = get_parents(assets_by_name, asset_name);
        chain.pop(); // exclude self

        let own_vars = own_vars_of(asset);
        let mut merged = own_vars.clone();

        for parent in &chain {
            let Some(parent_asset) = assets_by_name.get(parent.as_str()) else {
                continue;
            };
            let parent_own_vars = own_vars_of(parent_asset);
            if parent_own_vars.is_empty() {
                continue;
            }
            for name in own_vars.keys() {
                if parent_own_vars.contains_key(name) {
                    return Err(err(format!("Variable '{name}' previously defined")));
                }
            }
            for (name, expr) in &parent_own_vars {
                merged.entry(name.clone()).or_insert_with(|| expr.clone());
            }
        }

        resolved.insert(asset_name.to_string(), merged);
    }

    Ok(resolved)
}

/// Port of `_analyse_variables`'s final loop + `_variable_to_asset`: every
/// variable (own or inherited) must resolve to an asset, with cycle
/// detection.
fn validate_variables_resolve(ctx: &Ctx) -> Result<(), CompileError> {
    for (asset, vars) in &ctx.raw_vars {
        for (var_name, expr) in vars {
            let mut stack = Vec::new();
            match resolve_to_asset(ctx, asset, expr, &mut stack)? {
                Some(_) => {}
                None => {
                    return Err(err(format!(
                        "Variable '{var_name}' does not point to an asset"
                    )))
                }
            }
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------
// step-expression resolution (unifies _check_to_asset's family)
// ---------------------------------------------------------------------

fn resolve_to_asset(
    ctx: &Ctx,
    asset: &str,
    expr: &Value,
    var_stack: &mut Vec<String>,
) -> Result<Option<String>, CompileError> {
    match expr["type"].as_str().unwrap_or_default() {
        "field" => {
            let name = expr["name"].as_str().unwrap_or_default();
            Ok(ctx.fields.get(asset).and_then(|m| m.get(name)).cloned())
        }
        "variable" => {
            let name = expr["name"].as_str().unwrap_or_default();
            if var_stack.iter().any(|v| v == name) {
                let cycle = format!("{}->{name}", var_stack.join("->"));
                return Err(err(format!("Variable '{name}' contains cycle {cycle}")));
            }
            let Some(var_expr) = ctx.raw_vars.get(asset).and_then(|m| m.get(name)) else {
                return Ok(None);
            };
            var_stack.push(name.to_string());
            let result = resolve_to_asset(ctx, asset, var_expr, var_stack);
            var_stack.pop();
            result
        }
        "collect" => match resolve_to_asset(ctx, asset, &expr["lhs"], var_stack)? {
            Some(left) => resolve_to_asset(ctx, &left, &expr["rhs"], var_stack),
            None => Ok(None),
        },
        "union" | "intersection" | "difference" => {
            let lhs = resolve_to_asset(ctx, asset, &expr["lhs"], var_stack)?;
            let rhs = resolve_to_asset(ctx, asset, &expr["rhs"], var_stack)?;
            match (lhs, rhs) {
                (Some(l), Some(r)) => Ok(get_lca(&ctx.assets_by_name, &l, &r)),
                _ => Ok(None),
            }
        }
        "transitive" => match resolve_to_asset(ctx, asset, &expr["stepExpression"], var_stack)? {
            Some(res) if is_child(&ctx.assets_by_name, asset, &res) => Ok(Some(res)),
            _ => Ok(None),
        },
        "subType" => match resolve_to_asset(ctx, asset, &expr["stepExpression"], var_stack)? {
            Some(target) => {
                let sub_type = expr["subType"].as_str().unwrap_or_default();
                if !ctx.assets_by_name.contains_key(sub_type) {
                    return Err(err(format!("Asset '{sub_type}' not defined")));
                }
                if is_child(&ctx.assets_by_name, &target, sub_type) {
                    Ok(Some(sub_type.to_string()))
                } else {
                    Ok(None)
                }
            }
            None => Ok(None),
        },
        other => Err(err(format!("Unexpected expression '{other}'"))),
    }
}

fn resolve_to_step(
    ctx: &Ctx,
    asset: &str,
    expr: &Value,
    var_stack: &mut Vec<String>,
) -> Result<bool, CompileError> {
    match expr["type"].as_str().unwrap_or_default() {
        "attackStep" => {
            let name = expr["name"].as_str().unwrap_or_default();
            Ok(ctx.steps.get(asset).map(|s| s.contains(name)).unwrap_or(false))
        }
        "multiplicity" => Err(err(
            "`->` or `+>` with a statement that ends in a multiplicity qualifier (`:x`, `:x..y`, `:*`) is not supported",
        )),
        "collect" => match resolve_to_asset(ctx, asset, &expr["lhs"], var_stack)? {
            Some(left) => resolve_to_step(ctx, &left, &expr["rhs"], var_stack),
            None => Ok(false),
        },
        _ => Err(err("Last step is not attack step")),
    }
}

// ---------------------------------------------------------------------
// reaches / requires
// ---------------------------------------------------------------------

fn analyse_reaches(ctx: &Ctx, assets: &[Value]) -> Result<(), CompileError> {
    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();
        for step in asset["attackSteps"].as_array().into_iter().flatten() {
            let step_type = step["type"].as_str().unwrap_or_default();
            let requires = &step["requires"];
            let ttc = &step["ttc"];

            if step_type == "exist" || step_type == "notExist" {
                if !ttc.is_null() {
                    return Err(err(format!(
                        "Attack step of type '{step_type}' must not have TTC"
                    )));
                }
                if !requires.is_null() {
                    for expr in requires["stepExpressions"].as_array().into_iter().flatten() {
                        let mut stack = Vec::new();
                        if resolve_to_asset(ctx, asset_name, expr, &mut stack)?.is_none() {
                            return Err(err(
                                "All expressions in requires ('<-') must point to a valid asset",
                            ));
                        }
                    }
                } else {
                    return Err(err(format!(
                        "Attack step of type '{step_type}' must have require '<-'"
                    )));
                }
            } else if !requires.is_null() {
                return Err(err(
                    "Require '<-' may only be defined for attack step type exist 'E' or not-exist '!E'",
                ));
            }

            let reaches = &step["reaches"];
            if !reaches.is_null() {
                for expr in reaches["stepExpressions"].as_array().into_iter().flatten() {
                    let mut stack = Vec::new();
                    if !resolve_to_step(ctx, asset_name, expr, &mut stack)? {
                        return Err(err(
                            "All expressions in reaches ('->') must point to a valid attack step",
                        ));
                    }
                }
            }
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------
// CIA / TTC
// ---------------------------------------------------------------------

fn check_cia_and_ttc(assets: &[Value]) -> Result<(), CompileError> {
    for asset in assets {
        let asset_name = asset["name"].as_str().unwrap_or_default();
        for step in asset["attackSteps"].as_array().into_iter().flatten() {
            validate_cia(asset_name, step)?;
            validate_ttc(asset_name, step)?;
        }
    }
    Ok(())
}

fn validate_cia(asset_name: &str, step: &Value) -> Result<(), CompileError> {
    if step["risk"].is_null() {
        return Ok(());
    }
    let step_type = step["type"].as_str().unwrap_or_default();
    if matches!(step_type, "defense" | "exist" | "notExist") {
        let step_name = step["name"].as_str().unwrap_or_default();
        return Err(err(format!(
            "{asset_name}.{step_name}: {step_type}: Defenses cannot have CIA classifications"
        )));
    }
    Ok(())
}

fn validate_ttc(asset_name: &str, step: &Value) -> Result<(), CompileError> {
    let ttc = &step["ttc"];
    if ttc.is_null() {
        return Ok(());
    }
    let step_name = step["name"].as_str().unwrap_or_default();
    match step["type"].as_str().unwrap_or_default() {
        "defense" => {
            if ttc["type"].as_str() != Some("function") {
                return Err(err(format!(
                    "Defense {asset_name}.{step_name} may not have advanced TTC expressions"
                )));
            }
            match ttc["name"].as_str().unwrap_or_default() {
                "Enabled" | "Disabled" | "Bernoulli" => validate_distribution(ttc),
                _ => Err(err(format!(
                    "Defense {asset_name}.{step_name} may only have 'Enabled', 'Disabled', or 'Bernoulli(p)' as TTC"
                ))),
            }
        }
        "exist" | "notExist" => Ok(()),
        _ => check_ttc_expr(ttc, false),
    }
}

fn check_ttc_expr(expr: &Value, is_sub_div_exp: bool) -> Result<(), CompileError> {
    match expr["type"].as_str().unwrap_or_default() {
        "subtraction" | "exponentiation" | "division" => {
            check_ttc_expr(&expr["lhs"], true)?;
            check_ttc_expr(&expr["rhs"], true)
        }
        "multiplication" | "addition" => {
            check_ttc_expr(&expr["lhs"], false)?;
            check_ttc_expr(&expr["rhs"], false)
        }
        "function" => {
            let name = expr["name"].as_str().unwrap_or_default();
            if matches!(name, "Enabled" | "Disabled") {
                return Err(err(
                    "Distributions 'Enabled' or 'Disabled' may not be used as TTC values in '&' and '|' attack steps",
                ));
            }
            if is_sub_div_exp && matches!(name, "Bernoulli" | "EasyAndUncertain") {
                return Err(err(format!(
                    "TTC distribution '{name}' is not available in subtraction, division or exponential expressions."
                )));
            }
            validate_distribution(expr)
        }
        "number" => Ok(()),
        other => Err(err(format!("Unexpected expression '{other}'"))),
    }
}

fn validate_distribution(function_expr: &Value) -> Result<(), CompileError> {
    let name = function_expr["name"].as_str().unwrap_or_default();
    let params: Vec<f64> = function_expr["arguments"]
        .as_array()
        .into_iter()
        .flatten()
        .filter_map(Value::as_f64)
        .collect();
    distributions::validate(name, &params).map_err(|e| err(e.0))
}
