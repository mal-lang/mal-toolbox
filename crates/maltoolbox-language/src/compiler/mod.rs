//! Port of mal-toolbox's `maltoolbox/language/compiler/mal_compiler.py`.
//!
//! Walks a tree-sitter-mal parse tree into the same loosely-typed
//! `langspec` JSON shape the Python compiler produces (formatVersion /
//! defines / categories / assets / associations), so downstream language-
//! graph building and file I/O can stay wire-compatible with the Python
//! mal-toolbox. This module (`compile_file`/`compile_inner`) only
//! replicates the structural visitor; semantic validation (port of
//! `mal_analyzer.py`) lives in the sibling [`semantic`] module and runs
//! once, at the end of `compile_file`, over the fully-merged langspec.
//!
//! Unlike the Python original, this walks the tree via tree-sitter's
//! *field* API (`child_by_field_name` / `children_by_field_name`) rather
//! than a raw cursor sibling-walk. Fields never include `comment` nodes
//! (tree-sitter `extra`s are only ever attached positionally), so this
//! sidesteps the comment-skipping dance `go_to_sibling` existed for in
//! the Python code. Positional (non-field) child iteration still has to
//! filter `comment` out explicitly - see `named_children_no_comments`.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::{json, Map, Value};
use tree_sitter::Node;

use crate::new_parser;

pub mod distributions;
pub mod semantic;

#[derive(Debug, thiserror::Error)]
pub enum CompileError {
    #[error("failed to read '{path}': {source}")]
    Io {
        path: PathBuf,
        #[source]
        source: std::io::Error,
    },
    #[error("syntax error in '{path}' at line {line}, column {column}")]
    Syntax {
        path: PathBuf,
        line: usize,
        column: usize,
    },
    #[error("malformed MAL source: {0}")]
    Malformed(String),
    #[error("{0}")]
    Semantic(String),
}

/// Compile a `.mal` file (and any `include`d files) into the langspec
/// JSON shape used by [`maltoolbox-model`]/the language-graph builder,
/// after running the semantic analyzer (port of `mal_analyzer.py`) over
/// the fully-merged result.
pub fn compile_file(path: impl AsRef<Path>) -> Result<Value, CompileError> {
    let mut visited = HashSet::new();
    let mut active: Vec<PathBuf> = Vec::new();
    let mut path_stack: Vec<PathBuf> = Vec::new();
    let mut seen_custom_defines = HashSet::new();
    let langspec = compile_inner(
        path.as_ref(),
        &mut visited,
        &mut active,
        &mut path_stack,
        &mut seen_custom_defines,
    )?;
    semantic::analyze(&langspec)?;
    Ok(langspec)
}

/// `active` holds the chain of files currently being compiled (the
/// include "call stack"), used for real cycle detection: finding
/// `current_file` in it means an include chain has looped back on
/// itself, anywhere in the chain - including back to the root file.
///
/// NOTE: the Python oracle's cycle detection (`mal_analyzer.py`'s
/// `_include_stack`) is confirmed buggy - it never raises for an include
/// cycle that loops back to the root file specifically, because the root
/// is never itself pushed as an "include" target (only files reached via
/// an `include_declaration` are). `mal_compiler.py`'s own `visited_files`
/// dedup also runs *before* the analyzer's per-include cycle check can
/// fire for such a cycle, since the root is already marked visited by
/// the time its own name is seen again. A genuine two-file mutual include
/// (A includes B includes A) therefore silently compiles with no error
/// in the real implementation. This Rust port intentionally diverges and
/// implements real cycle detection, since silently accepting a
/// structurally circular language spec seemed worse than matching that
/// bug.
fn compile_inner(
    malfile: &Path,
    visited: &mut HashSet<PathBuf>,
    active: &mut Vec<PathBuf>,
    path_stack: &mut Vec<PathBuf>,
    seen_custom_defines: &mut HashSet<String>,
) -> Result<Value, CompileError> {
    let mut current_file = malfile.to_path_buf();
    if !current_file.is_absolute() {
        if let Some(parent_dir) = path_stack.last() {
            current_file = parent_dir.join(&current_file);
        }
    }

    if let Some(cycle_start) = active.iter().position(|f| f == &current_file) {
        let mut chain: Vec<String> = active[cycle_start..]
            .iter()
            .map(|f| f.display().to_string())
            .collect();
        chain.push(current_file.display().to_string());
        return Err(CompileError::Semantic(format!(
            "Include sequence contains cycle: {}",
            chain.join(" -> ")
        )));
    }

    if visited.contains(&current_file) {
        // Already fully compiled via another, non-cyclic include path
        // (e.g. a "diamond": both B and C include A) - safe to skip
        // rather than recompile.
        return Ok(json!({}));
    }
    visited.insert(current_file.clone());
    active.push(current_file.clone());
    path_stack.push(
        current_file
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| PathBuf::from(".")),
    );

    let source = fs::read(&current_file).map_err(|e| CompileError::Io {
        path: current_file.clone(),
        source: e,
    })?;

    let mut parser = new_parser();
    let tree = parser
        .parse(&source, None)
        .ok_or_else(|| CompileError::Malformed("tree-sitter parser did not run".into()))?;
    let root = tree.root_node();

    if let Some(err_node) = first_error_node(root) {
        path_stack.pop();
        active.pop();
        return Err(CompileError::Syntax {
            path: current_file,
            line: err_node.start_position().row + 1,
            column: err_node.start_position().column + 1,
        });
    }

    let result = visit_source_file(root, &source, visited, active, path_stack, seen_custom_defines);
    path_stack.pop();
    active.pop();
    result
}

fn first_error_node(node: Node) -> Option<Node> {
    if node.is_error() || node.is_missing() {
        return Some(node);
    }
    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            if let Some(found) = first_error_node(child) {
                return Some(found);
            }
        }
    }
    None
}

fn text<'a>(node: Node, source: &'a [u8]) -> &'a str {
    node.utf8_text(source).unwrap_or("")
}

/// Positional children, skipping `comment` extras (which, unlike field
/// lookups, are *not* excluded from `named_child` iteration - verified
/// empirically against tree-sitter-mal 1.3.0).
fn named_children_no_comments<'a>(node: Node<'a>) -> impl Iterator<Item = Node<'a>> {
    (0..node.named_child_count())
        .filter_map(move |i| node.named_child(i))
        .filter(|n| n.kind() != "comment")
}

/// For fields that bundle optional surrounding punctuation under the same
/// field name (e.g. ttc_binop's parenthesized `left`/`right`), pick the
/// first *named* node tagged with `field`, skipping anonymous tokens like
/// `(`/`)`.
fn field_operand<'a>(node: Node<'a>, field: &'static str) -> Result<Node<'a>, CompileError> {
    let mut cursor = node.walk();
    let found = node
        .children_by_field_name(field, &mut cursor)
        .find(|n| n.is_named());
    found.ok_or_else(|| CompileError::Malformed(format!("expected operand for field '{field}'")))
}

fn required_field<'a>(node: Node<'a>, field: &'static str) -> Result<Node<'a>, CompileError> {
    node.child_by_field_name(field)
        .ok_or_else(|| CompileError::Malformed(format!("missing required field '{field}'")))
}

fn strip_quotes(s: &str) -> &str {
    let bytes = s.as_bytes();
    if bytes.len() >= 2 && bytes[0] == b'"' && bytes[bytes.len() - 1] == b'"' {
        &s[1..s.len() - 1]
    } else {
        s
    }
}

fn insert_object(value: &mut Value, key: &str, entry_key: String, entry_value: Value) {
    value[key]
        .as_object_mut()
        .expect("langspec field should be an object")
        .insert(entry_key, entry_value);
}

fn extend_array(value: &mut Value, key: &str, items: Vec<Value>) {
    value[key]
        .as_array_mut()
        .expect("langspec field should be an array")
        .extend(items);
}

fn dedup_array_in_place(arr: &mut Vec<Value>) {
    let mut unique: Vec<Value> = Vec::with_capacity(arr.len());
    for item in arr.drain(..) {
        if !unique.contains(&item) {
            unique.push(item);
        }
    }
    *arr = unique;
}

// ---------------------------------------------------------------------
// source_file / declaration
// ---------------------------------------------------------------------

fn visit_source_file(
    root: Node,
    source: &[u8],
    visited: &mut HashSet<PathBuf>,
    active: &mut Vec<PathBuf>,
    path_stack: &mut Vec<PathBuf>,
    seen_custom_defines: &mut HashSet<String>,
) -> Result<Value, CompileError> {
    let mut langspec = json!({
        "formatVersion": "1.0.0",
        "defines": {},
        "categories": [],
        "assets": [],
        "associations": [],
    });

    for declaration in named_children_no_comments(root) {
        // `declaration` is a transparent wrapper around exactly one of
        // the four top-level alternatives.
        let variant = declaration
            .named_child(0)
            .ok_or_else(|| CompileError::Malformed("empty top-level declaration".into()))?;

        match variant.kind() {
            "category_declaration" => {
                let (category, assets) = visit_category_declaration(variant, source)?;
                extend_array(&mut langspec, "categories", vec![category]);
                extend_array(&mut langspec, "assets", assets);
            }
            "define_declaration" => {
                let (key, value) = visit_define_declaration(variant, source)?;
                if key != "id" && key != "version" && !seen_custom_defines.insert(key.clone()) {
                    return Err(CompileError::Semantic(format!(
                        "Define '{key}' previously defined"
                    )));
                }
                insert_object(&mut langspec, "defines", key, Value::String(value));
            }
            "associations_declaration" => {
                let associations = visit_associations_declaration(variant, source)?;
                extend_array(&mut langspec, "associations", associations);
            }
            "include_declaration" => {
                let included_path = visit_include_declaration(variant, source)?;
                let included = compile_inner(
                    Path::new(&included_path),
                    visited,
                    active,
                    path_stack,
                    seen_custom_defines,
                )?;
                if let Some(defines) = included.get("defines").and_then(Value::as_object) {
                    for (k, v) in defines {
                        insert_object(&mut langspec, "defines", k.clone(), v.clone());
                    }
                }
                for key in ["categories", "assets", "associations"] {
                    if let Some(items) = included.get(key).and_then(Value::as_array) {
                        extend_array(&mut langspec, key, items.clone());
                    }
                }
            }
            other => {
                return Err(CompileError::Malformed(format!(
                    "unexpected top-level declaration: {other}"
                )))
            }
        }
    }

    for key in ["categories", "assets", "associations"] {
        if let Some(arr) = langspec[key].as_array_mut() {
            let mut owned = std::mem::take(arr);
            dedup_array_in_place(&mut owned);
            langspec[key] = Value::Array(owned);
        }
    }

    Ok(langspec)
}

fn visit_define_declaration(node: Node, source: &[u8]) -> Result<(String, String), CompileError> {
    let key = text(required_field(node, "id")?, source).to_string();
    let raw_value = text(required_field(node, "value")?, source);
    Ok((key, strip_quotes(raw_value).to_string()))
}

fn visit_include_declaration(node: Node, source: &[u8]) -> Result<String, CompileError> {
    let raw = text(required_field(node, "file")?, source);
    // mirrors Python's `[1:-1]` slice: strip exactly one leading/trailing byte.
    Ok(raw[1..raw.len() - 1].to_string())
}

fn visit_meta(node: Node, source: &[u8]) -> Result<(String, String), CompileError> {
    let key = text(required_field(node, "id")?, source).to_string();
    let raw_info = text(required_field(node, "info")?, source);
    Ok((key, raw_info[1..raw_info.len() - 1].to_string()))
}

fn visit_meta_fields(node: Node, source: &[u8], field: &'static str) -> Result<Map<String, Value>, CompileError> {
    let mut meta = Map::new();
    let mut cursor = node.walk();
    for meta_node in node.children_by_field_name(field, &mut cursor) {
        let (k, v) = visit_meta(meta_node, source)?;
        if meta.contains_key(&k) {
            return Err(CompileError::Semantic(format!(
                "Metadata '{k}' previously defined"
            )));
        }
        meta.insert(k, Value::String(v));
    }
    Ok(meta)
}

// ---------------------------------------------------------------------
// categories / assets
// ---------------------------------------------------------------------

fn visit_category_declaration(
    node: Node,
    source: &[u8],
) -> Result<(Value, Vec<Value>), CompileError> {
    let name = text(required_field(node, "id")?, source).to_string();
    let meta = visit_meta_fields(node, source, "meta")?;

    let mut assets = Vec::new();
    let mut cursor = node.walk();
    for asset_node in node.children_by_field_name("assets", &mut cursor) {
        assets.push(visit_asset_declaration(asset_node, source, &name)?);
    }

    let category = json!({ "name": name, "meta": meta });
    Ok((category, assets))
}

fn has_abstract_keyword(node: Node) -> bool {
    (0..node.child_count()).any(|i| {
        node.child(i)
            .map(|c| c.kind() == "abstract")
            .unwrap_or(false)
    })
}

fn visit_asset_declaration(node: Node, source: &[u8], category: &str) -> Result<Value, CompileError> {
    let name = text(required_field(node, "id")?, source).to_string();
    let is_abstract = has_abstract_keyword(node);

    let mut super_asset: Option<String> = None;
    let mut cursor = node.walk();
    for extends_node in node.children_by_field_name("extends", &mut cursor) {
        if extends_node.is_named() && extends_node.kind() == "identifier" {
            super_asset = Some(text(extends_node, source).to_string());
        }
    }

    let meta = visit_meta_fields(node, source, "meta")?;

    let (variables, attack_steps) = match node.child_by_field_name("body") {
        Some(body) => visit_asset_definition(body, source, &name)?,
        None => (Vec::new(), Vec::new()),
    };

    Ok(json!({
        "name": name,
        "meta": meta,
        "category": category,
        "isAbstract": is_abstract,
        "superAsset": super_asset,
        "variables": variables,
        "attackSteps": attack_steps,
    }))
}

fn visit_asset_definition(
    node: Node,
    source: &[u8],
    asset_name: &str,
) -> Result<(Vec<Value>, Vec<Value>), CompileError> {
    let mut variables = Vec::new();
    let mut steps = Vec::new();
    for child in named_children_no_comments(node) {
        match child.kind() {
            "asset_variable" => variables.push(visit_asset_variable(child, source)?),
            "attack_step" => steps.push(visit_attack_step(child, source, asset_name)?),
            other => {
                return Err(CompileError::Malformed(format!(
                    "unexpected child of asset_definition: {other}"
                )))
            }
        }
    }
    Ok((variables, steps))
}

fn visit_asset_variable(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let name = text(required_field(node, "id")?, source).to_string();
    let step_expression = visit_asset_expr(required_field(node, "value")?, source)?;
    Ok(json!({ "name": name, "stepExpression": step_expression }))
}

// ---------------------------------------------------------------------
// attack steps
// ---------------------------------------------------------------------

fn step_type_name(raw: &str) -> String {
    match raw {
        "&" => "and".to_string(),
        "|" => "or".to_string(),
        "#" => "defense".to_string(),
        "E" => "exist".to_string(),
        "!E" => "notExist".to_string(),
        other => other.to_string(),
    }
}

fn visit_attack_step(node: Node, source: &[u8], asset_name: &str) -> Result<Value, CompileError> {
    let step_type = step_type_name(text(required_field(node, "step_type")?, source));

    let causal_mode = node
        .child_by_field_name("causal_mode")
        .map(|n| text(n, source).to_string());

    let name = text(required_field(node, "id")?, source).to_string();

    let mut tags = Vec::new();
    let mut tag_cursor = node.walk();
    for tag_node in node.children_by_field_name("tag", &mut tag_cursor) {
        if tag_node.is_named() {
            tags.push(Value::String(text(tag_node, source).to_string()));
        }
    }

    let mut risk = Value::Null;
    let mut cias_cursor = node.walk();
    for cias_field_node in node.children_by_field_name("cias", &mut cias_cursor) {
        if cias_field_node.is_named() && cias_field_node.kind() == "cias" {
            risk = visit_cias(cias_field_node, source, asset_name, &name);
        }
    }

    let ttc = match node.child_by_field_name("ttc") {
        Some(ttc_node) => visit_ttc(ttc_node, source)?,
        None => Value::Null,
    };

    let meta = visit_meta_fields(node, source, "meta")?;

    let mut detectors = Map::new();
    let mut det_cursor = node.walk();
    for det_node in node.children_by_field_name("detector", &mut det_cursor) {
        let detector = visit_detector(det_node, source)?;
        let det_name = detector
            .get("name")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        detectors.insert(det_name, detector);
    }

    let requires = match node.child_by_field_name("preconditions") {
        Some(pre_node) => visit_preconditions(pre_node, source)?,
        None => Value::Null,
    };

    let mut reaches = Value::Null;
    let mut append_reaches = Value::Null;
    let mut remove_reaches = Value::Null;
    let mut reach_cursor = node.walk();
    for reach_node in node.children_by_field_name("reaches", &mut reach_cursor) {
        match reach_node.kind() {
            "reaching" => reaches = visit_reaching(reach_node, source)?,
            "append_reaching" => append_reaches = visit_append_reaching(reach_node, source)?,
            "remove_reaching" => remove_reaches = visit_remove_reaching(reach_node, source)?,
            _ => {}
        }
    }

    Ok(json!({
        "name": name,
        "meta": meta,
        "detectors": detectors,
        "type": step_type,
        "causal_mode": causal_mode,
        "tags": tags,
        "risk": risk,
        "ttc": ttc,
        "requires": requires,
        "reaches": reaches,
        "append_reaches": append_reaches,
        "remove_reaches": remove_reaches,
    }))
}

/// Port of `visit_cias`, plus `mal_analyzer.py`'s `_validate_CIA`
/// duplicate-classification warning (e.g. `C, C, I`), which Python emits
/// as a side effect of the same walk. Only the first duplicate warns,
/// matching the Python original's early `return` after it finds one -
/// but unlike Python, finding a duplicate never skips building `risk`
/// for the remaining letters, since that part of the original walk is
/// not analyzer-gated and skipping it here would change serialized
/// output.
fn visit_cias(node: Node, source: &[u8], asset_name: &str, step_name: &str) -> Value {
    let mut risk = json!({
        "isConfidentiality": false,
        "isIntegrity": false,
        "isAvailability": false,
    });
    let mut seen = HashSet::new();
    let mut warned = false;
    for cia_node in named_children_no_comments(node) {
        if cia_node.kind() != "cia" {
            continue;
        }
        let letter = text(cia_node, source);
        let key = match letter {
            "C" => "isConfidentiality",
            "I" => "isIntegrity",
            "A" => "isAvailability",
            _ => continue,
        };
        if !warned && !seen.insert(letter) {
            eprintln!(
                "warning: attack step {asset_name}.{step_name} contains duplicate classification {letter}"
            );
            warned = true;
        }
        risk[key] = Value::Bool(true);
    }
    risk
}

// ---------------------------------------------------------------------
// detectors
// ---------------------------------------------------------------------

fn visit_detector(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let name = node
        .child_by_field_name("name")
        .map(|n| text(n, source).to_string());

    let context = match node.child_by_field_name("context") {
        Some(ctx_node) => visit_detector_context(ctx_node, source)?,
        None => Value::Object(Map::new()),
    };

    let detector_type = node
        .child_by_field_name("type")
        .map(|n| text(n, source).to_string());

    let (tprate, fprate) = match node.child_by_field_name("tp_fp_rate") {
        Some(rate_node) => visit_tp_fp_rate(rate_node, source)?,
        None => (None, None),
    };

    Ok(json!({
        "name": name,
        "context": context,
        "type": detector_type,
        "tprate": tprate,
        "fprate": fprate,
    }))
}

fn visit_detector_context(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let mut context = Map::new();
    for reference_node in named_children_no_comments(node) {
        if reference_node.kind() != "detector_context_reference" {
            continue;
        }
        let (label, value) = visit_detector_context_reference(reference_node, source)?;
        context.insert(label, value);
    }
    Ok(Value::Object(context))
}

fn visit_detector_context_reference(
    node: Node,
    source: &[u8],
) -> Result<(String, Value), CompileError> {
    let ctx_step = required_field(node, "ctx_step")?;
    let context_ref_text = text(ctx_step, source).to_string();
    let context = visit_asset_expr(ctx_step, source)?;

    let label = match node.child_by_field_name("id") {
        Some(id_node) => text(id_node, source).to_string(),
        None => context_ref_text,
    };

    Ok((label, context))
}

fn parse_number(node: Node, source: &[u8]) -> Result<f64, CompileError> {
    text(node, source)
        .parse::<f64>()
        .map_err(|_| CompileError::Malformed(format!("invalid number: {}", text(node, source))))
}

fn visit_tp_fp_rate(
    node: Node,
    source: &[u8],
) -> Result<(Option<f64>, Option<f64>), CompileError> {
    let inner = named_children_no_comments(node)
        .next()
        .ok_or_else(|| CompileError::Malformed("empty tp_fp_rate".into()))?;

    match inner.kind() {
        "tpr_only" => {
            let rate = parse_number(required_field(inner, "tp_rate")?, source)?;
            Ok((Some(rate), None))
        }
        "fpr_only" => {
            let rate = parse_number(required_field(inner, "fp_rate")?, source)?;
            Ok((None, Some(rate)))
        }
        "tp_fp_pair" => {
            let tp = parse_number(required_field(inner, "tp_rate")?, source)?;
            let fp = parse_number(required_field(inner, "fp_rate")?, source)?;
            Ok((Some(tp), Some(fp)))
        }
        other => Err(CompileError::Malformed(format!(
            "unknown tp/fp rate node: {other}"
        ))),
    }
}

// ---------------------------------------------------------------------
// TTC
// ---------------------------------------------------------------------

fn visit_ttc(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let inner = named_children_no_comments(node)
        .next()
        .ok_or_else(|| CompileError::Malformed("empty ttc".into()))?;
    visit_ttc_operand(inner, source)
}

fn visit_ttc_operand(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    match node.kind() {
        "float" | "integer" => Ok(json!({ "type": "number", "value": parse_number(node, source)? })),
        "identifier" => Ok(json!({
            "type": "function",
            "name": text(node, source),
            "arguments": [],
        })),
        "ttc_distribution" => visit_ttc_distribution(node, source),
        "ttc_binop" => visit_ttc_binop(node, source),
        other => Err(CompileError::Malformed(format!(
            "unexpected ttc expression node: {other}"
        ))),
    }
}

fn ttc_binop_name(op: &str) -> Option<&'static str> {
    match op {
        "+" => Some("addition"),
        "-" => Some("subtraction"),
        "*" => Some("multiplication"),
        "/" => Some("division"),
        "^" => Some("exponentiation"),
        _ => None,
    }
}

fn visit_ttc_binop(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let left = field_operand(node, "left")?;
    let right = field_operand(node, "right")?;
    let operator = text(required_field(node, "operator")?, source);
    let op_name = ttc_binop_name(operator)
        .ok_or_else(|| CompileError::Malformed(format!("unknown ttc operator: {operator}")))?;

    Ok(json!({
        "type": op_name,
        "lhs": visit_ttc_operand(left, source)?,
        "rhs": visit_ttc_operand(right, source)?,
    }))
}

fn visit_ttc_distribution(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let name = text(required_field(node, "id")?, source).to_string();

    let mut arguments = Vec::new();
    let mut cursor = node.walk();
    for value_node in node.children_by_field_name("values", &mut cursor) {
        if value_node.is_named() {
            arguments.push(Value::from(parse_number(value_node, source)?));
        }
    }

    Ok(json!({ "type": "function", "name": name, "arguments": arguments }))
}

// ---------------------------------------------------------------------
// preconditions / reaches
// ---------------------------------------------------------------------

fn visit_preconditions(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let mut step_expressions = Vec::new();
    let mut cursor = node.walk();
    for cond_node in node.children_by_field_name("condition", &mut cursor) {
        if cond_node.is_named() {
            step_expressions.push(visit_asset_expr(cond_node, source)?);
        }
    }
    Ok(json!({ "overrides": true, "stepExpressions": step_expressions }))
}

fn visit_reaching(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let operator = text(required_field(node, "operator")?, source);
    let overrides = operator == "->";

    let mut step_expressions = Vec::new();
    let mut cursor = node.walk();
    for reach_node in node.children_by_field_name("reaches", &mut cursor) {
        if reach_node.is_named() {
            step_expressions.push(visit_asset_expr(reach_node, source)?);
        }
    }
    Ok(json!({ "overrides": overrides, "stepExpressions": step_expressions }))
}

fn visit_append_reaching(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let operator = text(required_field(node, "operator")?, source);
    let overrides = operator == "A>";

    let mut step_expressions = Vec::new();
    let mut cursor = node.walk();
    for reach_node in node.children_by_field_name("reaches", &mut cursor) {
        if reach_node.is_named() {
            step_expressions.push(visit_dyn_sentence(reach_node, source)?);
        }
    }
    Ok(json!({ "overrides": overrides, "stepExpressions": step_expressions }))
}

fn visit_remove_reaching(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let operator = text(required_field(node, "operator")?, source);
    let overrides = operator == "R>";

    let mut step_expressions = Vec::new();
    let mut cursor = node.walk();
    for reach_node in node.children_by_field_name("reaches", &mut cursor) {
        if reach_node.is_named() {
            step_expressions.push(visit_dyn_sentence(reach_node, source)?);
        }
    }
    Ok(json!({ "overrides": overrides, "stepExpressions": step_expressions }))
}

fn visit_dyn_sentence(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let base = visit_asset_expr(required_field(node, "base")?, source)?;

    let mut targets = Vec::new();
    for child in named_children_no_comments(node) {
        if child.kind() == "assoc_and_asset_expr" {
            targets.push(visit_assoc_and_asset_expr(child, source)?);
        }
    }

    Ok(json!({ "type": "dyn_sentence", "base": base, "targets": targets }))
}

fn visit_assoc_and_asset_expr(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let children: Vec<Node> = named_children_no_comments(node).collect();
    if let Some(assoc_op_node) = children.iter().find(|n| n.kind() == "assoc_op") {
        let operand_node = children
            .iter()
            .find(|n| n.kind() != "assoc_op")
            .ok_or_else(|| CompileError::Malformed("assoc_op without operand".into()))?;
        let _ = assoc_op_node; // operator text currently unused downstream, mirrors Python's dict
        Ok(json!({
            "type": "assoc_op",
            "operand": visit_asset_expr(*operand_node, source)?,
        }))
    } else {
        let operand_node = children
            .first()
            .ok_or_else(|| CompileError::Malformed("empty assoc_and_asset_expr".into()))?;
        visit_asset_expr(*operand_node, source)
    }
}

// ---------------------------------------------------------------------
// asset expressions
// ---------------------------------------------------------------------

fn visit_asset_expr(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    // `asset_expr` is a transparent single-child wrapper node.
    if node.kind() == "asset_expr" {
        let inner = named_children_no_comments(node)
            .next()
            .ok_or_else(|| CompileError::Malformed("empty asset_expr".into()))?;
        return visit_asset_expr_operand(inner, source);
    }
    visit_asset_expr_operand(node, source)
}

fn visit_asset_expr_operand(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    match node.kind() {
        "asset_expr" => visit_asset_expr(node, source),
        "identifier" => {
            let role = resolve_identifier_role(node, source);
            Ok(json!({ "type": role, "name": text(node, source) }))
        }
        "asset_variable_substitution" => Ok(json!({
            "type": "variable",
            "name": text(required_field(node, "id")?, source),
        })),
        "asset_expr_binop" => visit_asset_expr_binop(node, source),
        "asset_expr_multiplicity" => visit_asset_expr_multiplicity(node, source),
        "asset_expr_type" => visit_asset_expr_type(node, source),
        "asset_expr_unop" => visit_asset_expr_unop(node, source),
        other => Err(CompileError::Malformed(format!(
            "unexpected asset expression node: {other}"
        ))),
    }
}

fn binop_name(op: &str) -> Option<&'static str> {
    match op {
        "." => Some("collect"),
        "\\/" => Some("union"),
        "/\\" => Some("intersection"),
        "-" => Some("difference"),
        _ => None,
    }
}

fn visit_asset_expr_binop(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let left = field_operand(node, "left")?;
    let right = field_operand(node, "right")?;
    let operator = text(required_field(node, "operator")?, source);
    let op_name = binop_name(operator)
        .ok_or_else(|| CompileError::Malformed(format!("unknown asset expr operator: {operator}")))?;

    Ok(json!({
        "type": op_name,
        "lhs": visit_asset_expr_operand(left, source)?,
        "rhs": visit_asset_expr_operand(right, source)?,
    }))
}

fn visit_asset_expr_multiplicity(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let expression = field_operand(node, "expression")?;
    let step_expression = visit_asset_expr_operand(expression, source)?;
    let multiplicity = visit_multiplicity(required_field(node, "multiplicity")?, source)?;
    Ok(json!({
        "type": "multiplicity",
        "multiplicity": multiplicity,
        "stepExpression": step_expression,
    }))
}

fn visit_asset_expr_type(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let expression = field_operand(node, "expression")?;
    let step_expression = visit_asset_expr_operand(expression, source)?;
    let sub_type = text(required_field(node, "type_id")?, source).to_string();
    Ok(json!({
        "type": "subType",
        "subType": sub_type,
        "stepExpression": step_expression,
    }))
}

fn visit_asset_expr_unop(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let expression = field_operand(node, "expression")?;
    let step_expression = visit_asset_expr_operand(expression, source)?;
    Ok(json!({ "type": "transitive", "stepExpression": step_expression }))
}

/// Port of `_resolve_part_ID_type` from mal_compiler.py. For a bare
/// identifier used as an asset expression, decides whether it denotes a
/// `field` or an `attackStep`.
///
/// This replicates the *exact* (slightly surprising) behaviour of the
/// Python original rather than a "cleaner" structural reinterpretation:
/// walk up to the nearest ancestor of type `reaching` or
/// `detector_context_reference` *specifically* (not `append_reaching`/
/// `remove_reaching`/`dyn_sentence`, which are not matched); if none is
/// found, the identifier is always a `field` (covers `let` bindings and
/// preconditions, but also - as a quirk - every identifier reached only
/// through `append_reaching`/`remove_reaching`). If found, scan the
/// ancestor's raw source text starting right after the identifier: the
/// first `.` byte means `field` (more chain follows), the first `,` or
/// end-of-text means `attackStep`.
fn resolve_identifier_role(identifier: Node, source: &[u8]) -> &'static str {
    let mut parent = identifier.parent();
    while let Some(p) = parent {
        if p.kind() == "reaching" || p.kind() == "detector_context_reference" {
            break;
        }
        parent = p.parent();
    }

    let Some(ancestor) = parent else {
        return "field";
    };

    let ancestor_start = ancestor.start_byte();
    let scan_start = identifier.end_byte() - ancestor_start;
    let ancestor_text = &source[ancestor.start_byte()..ancestor.end_byte()];

    for &byte in &ancestor_text[scan_start.min(ancestor_text.len())..] {
        match byte {
            b'.' => return "field",
            b',' => return "attackStep",
            _ => {}
        }
    }
    "attackStep"
}

// ---------------------------------------------------------------------
// multiplicity / associations
// ---------------------------------------------------------------------

fn visit_multiplicity(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let inner = named_children_no_comments(node)
        .next()
        .ok_or_else(|| CompileError::Malformed("empty multiplicity".into()))?;

    if inner.kind() == "multiplicity_range" {
        return visit_multiplicity_range(inner, source);
    }

    Ok(json!({ "min": text(inner, source), "max": Value::Null }))
}

fn visit_multiplicity_range(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let start = required_field(node, "start")?;
    let end = required_field(node, "end")?;
    Ok(json!({ "min": text(start, source), "max": text(end, source) }))
}

/// Normalizes a raw multiplicity atom (`"*"`, `"3"`, or already-null) into
/// its final numeric form, mirroring `_process_multitudes`:
/// - `max` defaults to `min` when absent.
/// - `*` means 0 for `min`, unbounded (`null`) for `max`.
/// - numeric strings become integers.
fn normalize_multiplicity(mult: &mut Value) {
    let min_raw = mult.get("min").cloned().unwrap_or(Value::Null);
    if mult.get("max").map(Value::is_null).unwrap_or(true) {
        mult["max"] = min_raw.clone();
    }
    for key in ["min", "max"] {
        let resolved = match mult.get(key) {
            Some(Value::String(s)) if s == "*" => {
                if key == "min" {
                    Value::from(0)
                } else {
                    Value::Null
                }
            }
            Some(Value::String(s)) => match s.parse::<i64>() {
                Ok(n) => Value::from(n),
                Err(_) => Value::String(s.clone()),
            },
            Some(other) => other.clone(),
            None => Value::Null,
        };
        mult[key] = resolved;
    }
}

fn visit_association(node: Node, source: &[u8]) -> Result<Value, CompileError> {
    let left_asset = text(required_field(node, "left_id")?, source).to_string();
    let left_field = text(required_field(node, "left_field_id")?, source).to_string();
    let mut left_multiplicity = visit_multiplicity(required_field(node, "left_mult")?, source)?;

    let name = text(required_field(node, "id")?, source).to_string();

    let mut right_multiplicity = visit_multiplicity(required_field(node, "right_mult")?, source)?;
    let right_field = text(required_field(node, "right_field_id")?, source).to_string();
    let right_asset = text(required_field(node, "right_id")?, source).to_string();

    let meta = visit_meta_fields(node, source, "meta")?;

    normalize_multiplicity(&mut left_multiplicity);
    normalize_multiplicity(&mut right_multiplicity);

    Ok(json!({
        "name": name,
        "meta": meta,
        "leftAsset": left_asset,
        "leftField": left_field,
        "leftMultiplicity": left_multiplicity,
        "rightAsset": right_asset,
        "rightField": right_field,
        "rightMultiplicity": right_multiplicity,
    }))
}

fn visit_associations_declaration(node: Node, source: &[u8]) -> Result<Vec<Value>, CompileError> {
    let mut associations = Vec::new();
    for child in named_children_no_comments(node) {
        if child.kind() == "association" {
            associations.push(visit_association(child, source)?);
        }
    }
    Ok(associations)
}
