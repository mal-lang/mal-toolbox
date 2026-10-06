//! Port of the file-loading/saving parts of `languagegraph.py`:
//! `from_mal_spec`, `from_mar_archive`, `language_graph_to_dict`/
//! `language_graph_from_dict`, and `load_language_graph_from_file`.
//! `language_graph_from_git_url` is out of scope (needs a git clone, and
//! isn't used by anything in this rewrite's scope).

use std::collections::HashMap;
use std::io::Read;
use std::path::Path;
use std::rc::Rc;

use indexmap::IndexMap;
use serde_json::Value;
use slotmap::SlotMap;

use super::asset::LanguageGraphAsset;
use super::assoc::{LanguageGraphAssociation, LanguageGraphAssociationField};
use super::attack_step::{AttackStepType, CausalMode, LanguageGraphAttackStep};
use super::expr_chain::ExpressionsChain;
use super::ids::AttackStepId;
use super::{language_graph_to_dict, GraphError, LanguageGraph, Metadata};
use crate::compiler::{compile_file, CompileError};

#[derive(Debug, thiserror::Error)]
pub enum LoadError {
    #[error("{0}")]
    Compile(#[from] CompileError),
    #[error("{0}")]
    Graph(#[from] GraphError),
    #[error("{0}")]
    FileUtil(#[from] maltoolbox_fileutil::FileUtilError),
    #[error("failed to read mar archive '{0}': {1}")]
    Archive(String, String),
    #[error("Unknown file extension, expected json/mal/mar/yml/yaml")]
    UnknownExtension,
}

pub fn from_mal_spec(path: impl AsRef<Path>) -> Result<LanguageGraph, LoadError> {
    let spec = compile_file(path.as_ref())?;
    super::generate_graph(spec).map_err(LoadError::from)
}

pub fn from_mar_archive(path: impl AsRef<Path>) -> Result<LanguageGraph, LoadError> {
    let path = path.as_ref();
    let file = std::fs::File::open(path)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let mut archive = zip::ZipArchive::new(file)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let mut entry = archive
        .by_name("langspec.json")
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let mut contents = String::new();
    entry
        .read_to_string(&mut contents)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let spec: Value = serde_json::from_str(&contents)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    super::generate_graph(spec).map_err(LoadError::from)
}

/// Save `graph.lang_spec` (the compiled langspec, *not* the full
/// `language_graph_to_dict` form) into a `.mar` zip archive as
/// `langspec.json`. A graph rebuilt via `language_graph_from_dict` never
/// has `lang_spec` set (matches the Python original), so round-tripping
/// such a graph through `.mar` writes `null`.
pub fn to_mar_archive(graph: &LanguageGraph, path: impl AsRef<Path>) -> Result<(), LoadError> {
    let path = path.as_ref();
    let file = std::fs::File::create(path)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let mut writer = zip::ZipWriter::new(file);
    let options = zip::write::SimpleFileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);
    writer
        .start_file("langspec.json", options)
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    let langspec_json =
        serde_json::to_string_pretty(&graph.lang_spec).expect("Value serialization cannot fail");
    use std::io::Write;
    writer
        .write_all(langspec_json.as_bytes())
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    writer
        .finish()
        .map_err(|e| LoadError::Archive(path.display().to_string(), e.to_string()))?;
    Ok(())
}

/// Save to JSON/YAML (the full `language_graph_to_dict` form) or `.mar`
/// (just `lang_spec`, see `to_mar_archive`), depending on `path`'s
/// extension.
pub fn save_to_file(graph: &LanguageGraph, path: impl AsRef<Path>) -> Result<(), LoadError> {
    let path_ref = path.as_ref();
    if path_ref.extension().and_then(|e| e.to_str()) == Some("mar") {
        return to_mar_archive(graph, path_ref);
    }
    let dict = language_graph_to_dict(graph)?;
    maltoolbox_fileutil::save_dict_to_file(path, &dict)?;
    Ok(())
}

pub fn load_from_file(path: impl AsRef<Path>) -> Result<LanguageGraph, LoadError> {
    let path = path.as_ref();
    match path.extension().and_then(|e| e.to_str()) {
        Some("mal") => from_mal_spec(path),
        Some("mar") => from_mar_archive(path),
        Some("yml") | Some("yaml") => {
            let dict = maltoolbox_fileutil::load_dict_from_yaml_file(path)?;
            language_graph_from_dict(&dict).map_err(LoadError::from)
        }
        Some("json") => {
            let dict = maltoolbox_fileutil::load_dict_from_json_file(path)?;
            language_graph_from_dict(&dict).map_err(LoadError::from)
        }
        _ => Err(LoadError::UnknownExtension),
    }
}

/// Rebuild a [`LanguageGraph`] from its serialized `to_dict` form
/// (`language_graph_to_dict`'s output), bypassing the langspec-driven
/// builder entirely - matches the Python original's
/// `language_graph_from_dict`.
pub fn language_graph_from_dict(serialized: &Value) -> Result<LanguageGraph, GraphError> {
    let obj = serialized.as_object().ok_or_else(|| {
        GraphError::Malformed("serialized language graph must be an object".into())
    })?;

    let metadata = Metadata {
        version: obj
            .get("metadata")
            .and_then(|m| m.get("version"))
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string(),
        id: obj
            .get("metadata")
            .and_then(|m| m.get("id"))
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string(),
    };

    let mut graph = LanguageGraph {
        assets: SlotMap::with_key(),
        steps: SlotMap::with_key(),
        asset_id_by_name: HashMap::new(),
        asset_order: Vec::new(),
        metadata,
        lang_spec: Value::Null,
    };

    let asset_dicts: Vec<(&String, &Value)> = obj
        .iter()
        .filter(|(k, _)| k.as_str() != "metadata")
        .collect();

    // Pass 1: create asset nodes.
    for (name, asset) in &asset_dicts {
        let node = LanguageGraphAsset {
            name: (*name).clone(),
            own_associations: IndexMap::new(),
            attack_steps: IndexMap::new(),
            info: str_map(&asset["info"]),
            own_super_asset: None,
            own_sub_assets: Vec::new(),
            own_variables: IndexMap::new(),
            is_abstract: asset["is_abstract"].as_bool().unwrap_or(false),
        };
        let id = graph.assets.insert(node);
        graph.asset_id_by_name.insert((*name).clone(), id);
        graph.asset_order.push(id);
    }

    // Pass 2: inheritance links.
    for (name, asset) in &asset_dicts {
        let asset_id = graph.asset_id_by_name[*name];
        if let Some(super_name) = asset["super_asset"].as_str().filter(|s| !s.is_empty()) {
            let super_id = graph
                .asset_id_by_name
                .get(super_name)
                .copied()
                .ok_or_else(|| GraphError::SuperAssetNotFound {
                    asset_name: (*name).clone(),
                    super_name: super_name.to_string(),
                })?;
            graph.assets[super_id].own_sub_assets.push(asset_id);
            graph.assets[asset_id].own_super_asset = Some(super_id);
        }
    }

    // Pass 3: associations.
    for (name, asset) in &asset_dicts {
        let asset_id = graph.asset_id_by_name[*name];
        let _ = asset_id;
        for assoc in asset["associations"]
            .as_object()
            .into_iter()
            .flatten()
            .map(|(_, v)| v)
        {
            let left_name = assoc["left"]["asset"].as_str().unwrap_or_default();
            let right_name = assoc["right"]["asset"].as_str().unwrap_or_default();
            let left_id = *graph.asset_id_by_name.get(left_name).ok_or_else(|| {
                GraphError::Malformed(format!(
                    "Left asset for association \"{}\" not found",
                    assoc["name"].as_str().unwrap_or_default()
                ))
            })?;
            let right_id = *graph.asset_id_by_name.get(right_name).ok_or_else(|| {
                GraphError::Malformed(format!(
                    "Right asset for association \"{}\" not found",
                    assoc["name"].as_str().unwrap_or_default()
                ))
            })?;

            let assoc_node = Rc::new(LanguageGraphAssociation {
                name: assoc["name"].as_str().unwrap_or_default().to_string(),
                left_field: LanguageGraphAssociationField {
                    asset: left_id,
                    fieldname: assoc["left"]["fieldname"]
                        .as_str()
                        .unwrap_or_default()
                        .to_string(),
                    minimum: assoc["left"]["min"].as_i64().unwrap_or(0),
                    maximum: assoc["left"]["max"].as_i64(),
                },
                right_field: LanguageGraphAssociationField {
                    asset: right_id,
                    fieldname: assoc["right"]["fieldname"]
                        .as_str()
                        .unwrap_or_default()
                        .to_string(),
                    minimum: assoc["right"]["min"].as_i64().unwrap_or(0),
                    maximum: assoc["right"]["max"].as_i64(),
                },
                info: str_map(&assoc["info"]),
            });

            let left_fieldname = assoc_node.left_field.fieldname.clone();
            let right_fieldname = assoc_node.right_field.fieldname.clone();
            graph.assets[left_id]
                .own_associations
                .insert(right_fieldname, assoc_node.clone());
            graph.assets[right_id]
                .own_associations
                .insert(left_fieldname, assoc_node);
        }
    }

    // Pass 4: variables.
    for (name, asset) in &asset_dicts {
        let asset_id = graph.asset_id_by_name[*name];
        for (var_name, entry) in asset["variables"].as_object().into_iter().flatten() {
            let target_name = entry[0].as_str().ok_or_else(|| {
                GraphError::Malformed(format!("variable \"{var_name}\" missing target asset name"))
            })?;
            let target_id = *graph.asset_id_by_name.get(target_name).ok_or_else(|| {
                GraphError::Malformed(format!("Unknown asset type \"{target_name}\""))
            })?;
            let chain = parse_expr_chain(&graph, &entry[1])?;
            graph.assets[asset_id]
                .own_variables
                .insert(var_name.clone(), (target_id, chain));
        }
    }

    // Pass 5: attack step nodes (without inheritance/children/parents/requires yet).
    let mut step_ids_by_full_name: HashMap<String, AttackStepId> = HashMap::new();
    for (name, asset) in &asset_dicts {
        let asset_id = graph.asset_id_by_name[*name];
        for (step_name, step) in asset["attack_steps"].as_object().into_iter().flatten() {
            let node = LanguageGraphAttackStep {
                name: step_name.clone(),
                step_type: AttackStepType::parse(step["type"].as_str().unwrap_or_default())?,
                asset: asset_id,
                causal_mode: step["causal_mode"].as_str().and_then(CausalMode::parse),
                ttc: Some(step["ttc"].clone()).filter(|v| !v.is_null()),
                overrides: step["overrides"].as_bool().unwrap_or(false),
                own_children: IndexMap::new(),
                own_parents: IndexMap::new(),
                own_additive_model_effects: Vec::new(),
                own_subtractive_model_effects: Vec::new(),
                info: str_map(&step["info"]),
                inherits: None,
                own_requires: Vec::new(),
                tags: step["tags"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .filter_map(|t| t.as_str().map(str::to_string))
                    .collect(),
                detectors: IndexMap::new(),
            };
            let full_name = format!("{name}:{step_name}");
            let id = graph.steps.insert(node);
            step_ids_by_full_name.insert(full_name, id);
            graph.assets[asset_id]
                .attack_steps
                .insert(step_name.clone(), id);
        }
    }

    // Pass 6: inheritance for attack steps.
    for (name, asset) in &asset_dicts {
        for (step_name, step) in asset["attack_steps"].as_object().into_iter().flatten() {
            let Some(inh) = step["inherits"].as_str() else {
                continue;
            };
            let step_id = step_ids_by_full_name[&format!("{name}:{step_name}")];
            let inh_id = *step_ids_by_full_name.get(inh).ok_or_else(|| {
                GraphError::Malformed(format!("Unknown inherited step \"{inh}\""))
            })?;
            graph.steps[step_id].inherits = Some(inh_id);
        }
    }

    // Pass 7: children/parents expression chains, and requirements.
    for (name, asset) in &asset_dicts {
        for (step_name, step) in asset["attack_steps"].as_object().into_iter().flatten() {
            let step_id = step_ids_by_full_name[&format!("{name}:{step_name}")];

            for (tgt_name, exprs) in step["own_children"].as_object().into_iter().flatten() {
                let tgt_id = *step_ids_by_full_name.get(tgt_name).ok_or_else(|| {
                    GraphError::Malformed(format!("Unknown attack step \"{tgt_name}\""))
                })?;
                let mut chains = Vec::new();
                for expr in exprs.as_array().into_iter().flatten() {
                    chains.push(parse_expr_chain(&graph, expr)?);
                }
                graph.steps[step_id]
                    .own_children
                    .entry(tgt_id)
                    .or_default()
                    .extend(chains);
            }
            for (tgt_name, exprs) in step["own_parents"].as_object().into_iter().flatten() {
                let tgt_id = *step_ids_by_full_name.get(tgt_name).ok_or_else(|| {
                    GraphError::Malformed(format!("Unknown attack step \"{tgt_name}\""))
                })?;
                let mut chains = Vec::new();
                for expr in exprs.as_array().into_iter().flatten() {
                    chains.push(parse_expr_chain(&graph, expr)?);
                }
                graph.steps[step_id]
                    .own_parents
                    .entry(tgt_id)
                    .or_default()
                    .extend(chains);
            }

            let step_type = AttackStepType::parse(step["type"].as_str().unwrap_or_default())?;
            if matches!(step_type, AttackStepType::Exist | AttackStepType::NotExist) {
                if let Some(reqs) = step.get("requires").and_then(Value::as_array) {
                    for expr in reqs {
                        if let Some(chain) = parse_expr_chain(&graph, expr)? {
                            graph.steps[step_id].own_requires.push(chain);
                        }
                    }
                }
            }
        }
    }

    Ok(graph)
}

fn str_map(v: &Value) -> HashMap<String, String> {
    v.as_object()
        .into_iter()
        .flatten()
        .filter_map(|(k, v)| v.as_str().map(|s| (k.clone(), s.to_string())))
        .collect()
}

/// Port of `ExpressionsChain._from_dict`. Resolves `FIELD` associations
/// by searching every asset's own associations for a name+fieldname
/// match (mirrors `_resolve_association`, which does the same via
/// `asset.associations`).
fn parse_expr_chain(
    graph: &LanguageGraph,
    data: &Value,
) -> Result<Option<ExpressionsChain>, GraphError> {
    if data.is_null() || (data.is_object() && data.as_object().unwrap().is_empty()) {
        return Ok(None);
    }
    let expr_type = data["type"]
        .as_str()
        .ok_or_else(|| GraphError::Malformed("Missing expressions chain type".into()))?;

    use super::expr_chain::ExprType;
    let parsed = match expr_type {
        "union" | "intersection" | "difference" | "collect" => {
            let op = match expr_type {
                "union" => ExprType::Union,
                "intersection" => ExprType::Intersection,
                "difference" => ExprType::Difference,
                _ => ExprType::Collect,
            };
            let payload = &data[expr_type];
            let left = parse_expr_chain(graph, &payload["left"])?;
            let right = parse_expr_chain(graph, &payload["right"])?;
            ExpressionsChain::Binary {
                op,
                left: left.map(Box::new),
                right: right.map(Box::new),
            }
        }
        "transitive" => ExpressionsChain::Transitive {
            sub: Box::new(
                parse_expr_chain(graph, &data["transitive"])?
                    .ok_or_else(|| GraphError::Malformed("TRANSITIVE requires sub_link".into()))?,
            ),
        },
        "subType" => {
            let sub = parse_expr_chain(graph, &data["expression"])?
                .ok_or_else(|| GraphError::Malformed("SUBTYPE requires sub_link".into()))?;
            let subtype_name = data["subType"]
                .as_str()
                .ok_or_else(|| GraphError::Malformed("SUBTYPE missing subType name".into()))?;
            let subtype = graph.asset_id(subtype_name).ok_or_else(|| {
                GraphError::Malformed(format!("Failed to find subtype {subtype_name}"))
            })?;
            ExpressionsChain::SubType {
                sub: Box::new(sub),
                subtype,
            }
        }
        "assoc_op" => ExpressionsChain::AssocOp {
            sub: Box::new(
                parse_expr_chain(graph, &data["operand"])?
                    .ok_or_else(|| GraphError::Malformed("ASSOC_OP requires sub_link".into()))?,
            ),
        },
        "field" => {
            let assoc_keys: Vec<&String> = data
                .as_object()
                .unwrap()
                .keys()
                .filter(|k| k.as_str() != "type")
                .collect();
            let [assoc_name] = assoc_keys[..] else {
                return Err(GraphError::Malformed(
                    "Invalid field expression format".into(),
                ));
            };
            let field_data = &data[assoc_name];
            let asset_name = field_data["asset type"].as_str().ok_or_else(|| {
                GraphError::Malformed("field expression missing asset type".into())
            })?;
            let fieldname = field_data["fieldname"].as_str().ok_or_else(|| {
                GraphError::Malformed("field expression missing fieldname".into())
            })?;
            let target_asset = graph.asset_id(asset_name).ok_or_else(|| {
                GraphError::Malformed(format!("Unknown asset type \"{asset_name}\""))
            })?;
            let association = graph
                .associations(target_asset)
                .values()
                .find(|a| a.name == *assoc_name && a.contains_fieldname(fieldname))
                .cloned()
                .ok_or_else(|| {
                    GraphError::Malformed(format!(
                        "Failed to find association \"{assoc_name}\" with fieldname \"{fieldname}\""
                    ))
                })?;
            ExpressionsChain::Field {
                association,
                fieldname: fieldname.to_string(),
            }
        }
        other => {
            return Err(GraphError::Malformed(format!(
                "Unknown expressions chain type {other}"
            )))
        }
    };
    Ok(Some(parsed))
}
