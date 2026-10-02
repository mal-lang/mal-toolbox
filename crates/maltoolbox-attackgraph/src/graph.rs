//! Port of `maltoolbox/attackgraph/attackgraph.py`'s `AttackGraph` class.
//! `attack_graph_from_dict`/`attack_graph_from_file` (deserialization)
//! are *not* ported - only `to_dict`/`save_to_file` are - since neither
//! CLI subcommand (`compile`, `generate-attack-graph`) ever reads an
//! attack graph back in; see `PORTING_NOTES.md` at the repo root.
//!
//! Holds `lang_graph` persistently (compiled once, never mutated, so an
//! `Rc` is safe to share) but *not* `model` - see the crate-level docs
//! for why methods that need the model take `&Model` explicitly instead.

use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use maltoolbox_language::graph::LanguageGraph;
use maltoolbox_model::Model;
use serde_json::{json, Map, Value};
use slotmap::SlotMap;

use crate::generate::{self, GeneratedGraph};
use crate::ids::AttackGraphNodeId;
use crate::node::AttackGraphNode;
use crate::node_getters::get_node_by_full_name;
use crate::partially_generate::{
    self, AssocAffectedDict,
};
use crate::GraphError;

pub struct AttackGraph {
    pub lang_graph: Rc<LanguageGraph>,
    pub nodes: SlotMap<AttackGraphNodeId, AttackGraphNode>,
    pub id_to_node: HashMap<i64, AttackGraphNodeId>,
    pub full_name_to_node: HashMap<String, AttackGraphNodeId>,
    pub attack_steps: Vec<AttackGraphNodeId>,
    pub defense_steps: Vec<AttackGraphNodeId>,
    pub next_node_id: i64,
}

impl AttackGraph {
    /// An empty graph with no nodes, mirroring `AttackGraph(lang_graph)`
    /// (no `model`).
    pub fn empty(lang_graph: Rc<LanguageGraph>) -> Self {
        AttackGraph {
            lang_graph,
            nodes: SlotMap::with_key(),
            id_to_node: HashMap::new(),
            full_name_to_node: HashMap::new(),
            attack_steps: Vec::new(),
            defense_steps: Vec::new(),
            next_node_id: 0,
        }
    }

    pub fn from_model(model: &Model) -> Result<Self, GraphError> {
        let generated = generate::generate_graph(model)?;
        Ok(Self::from_generated(model.lang_graph.clone(), generated))
    }

    fn from_generated(lang_graph: Rc<LanguageGraph>, generated: GeneratedGraph) -> Self {
        let next_node_id = generated.id_to_node.keys().max().map(|&m| m + 1).unwrap_or(0);
        AttackGraph {
            lang_graph,
            nodes: generated.nodes,
            id_to_node: generated.id_to_node,
            full_name_to_node: generated.full_name_to_node,
            attack_steps: generated.attack_steps,
            defense_steps: generated.defense_steps,
            next_node_id,
        }
    }

    /// Rebuild the whole graph from `model`, discarding the current
    /// contents. See `crate::generate::GeneratedGraph` for the full
    /// rebuild.
    pub fn regenerate_graph(&mut self, model: &Model) -> Result<(), GraphError> {
        let generated = generate::generate_graph(model)?;
        let rebuilt = Self::from_generated(model.lang_graph.clone(), generated);
        *self = rebuilt;
        Ok(())
    }

    /// Port of `AttackGraph.partially_regenerate_graph`. Updates the
    /// graph incrementally for the given model changes instead of a full
    /// `regenerate_graph` rebuild. `new_associations`/`removed_associations`
    /// are `(left_asset_id, fieldname, right_asset_id)` triples, mirroring
    /// the Python original's `(ModelAsset, str, ModelAsset)` tuples.
    /// Returns the newly created attack/defense step nodes.
    ///
    /// **Ordering contract for `removed_assets`** (this one differs from
    /// the Python original, and is the reason it's a contract rather
    /// than something that "just works" like it does there): this method
    /// looks removed assets up by id in `model` to resolve their language
    /// type and name, since nodes only ever store a `model_asset: i64`,
    /// not a live asset reference the way Python's `ModelAsset` objects
    /// stay readable even after being unlinked from `model.assets`. So
    /// the asset must still be present in `model` when this is called -
    /// call order must be: (1) remove its associations from the model,
    /// (2) call this method with it in `removed_assets`, (3) only then
    /// call `model.remove_asset` on it.
    pub fn partially_regenerate_graph(
        &mut self,
        model: &Model,
        new_assets: &HashSet<i64>,
        new_associations: &HashSet<(i64, String, i64)>,
        removed_assets: &HashSet<i64>,
        removed_associations: &HashSet<(i64, String, i64)>,
    ) -> Result<HashSet<AttackGraphNodeId>, GraphError> {
        let created = generate::create_nodes_from_assets(
            &mut self.nodes,
            new_assets,
            self.next_node_id,
            model,
        )?;

        self.next_node_id += created.id_to_node.len() as i64;
        self.id_to_node.extend(created.id_to_node);
        self.attack_steps.extend(created.attack_steps.iter().copied());
        self.defense_steps.extend(created.defense_steps.iter().copied());
        self.full_name_to_node.extend(created.full_name_to_node.clone());

        for &key in created.full_name_to_node.values() {
            generate::link_node_children(model, &mut self.nodes, key, &self.full_name_to_node)?;
        }

        let mut removed_assoc_dict: AssocAffectedDict = HashMap::new();
        for (left_id, fieldname, right_id) in removed_associations {
            removed_assoc_dict
                .entry(*left_id)
                .or_default()
                .entry(fieldname.clone())
                .or_default()
                .insert(*right_id);
            let opposite = partially_generate::switch_fieldname(model, *left_id, fieldname)?;
            removed_assoc_dict
                .entry(*right_id)
                .or_default()
                .entry(opposite)
                .or_default()
                .insert(*left_id);
        }

        let mut new_assoc_dict: AssocAffectedDict = HashMap::new();
        for (left_id, fieldname, right_id) in new_associations {
            new_assoc_dict
                .entry(*left_id)
                .or_default()
                .entry(fieldname.clone())
                .or_default()
                .insert(*right_id);
            let opposite = partially_generate::switch_fieldname(model, *left_id, fieldname)?;
            new_assoc_dict
                .entry(*right_id)
                .or_default()
                .entry(opposite)
                .or_default()
                .insert(*left_id);
        }

        let mut affected_assoc_dict: AssocAffectedDict = HashMap::new();
        for assoc_dict in [&new_assoc_dict, &removed_assoc_dict] {
            for (asset_id, fields) in assoc_dict {
                let dest_fields = affected_assoc_dict.entry(*asset_id).or_default();
                for (fieldname, assets) in fields {
                    dest_fields.entry(fieldname.clone()).or_default().extend(assets);
                }
            }
        }

        let nodes_of_modified_assoc =
            partially_generate::assoc_affected_nodes(model, &affected_assoc_dict, &self.full_name_to_node)?;
        for key in nodes_of_modified_assoc {
            partially_generate::correct_node_children_on_modified_assoc(
                model,
                &mut self.nodes,
                key,
                &self.full_name_to_node,
            )?;
        }

        generate::create_detectors(&mut self.nodes, &created.full_name_to_node, model)?;

        let removal_candidates =
            partially_generate::nodes_to_be_removed(removed_assets, model, &self.full_name_to_node)?;
        for candidate in removal_candidates {
            self.remove_node(candidate)?;
        }

        let mut result: HashSet<AttackGraphNodeId> = created.attack_steps.into_iter().collect();
        result.extend(created.defense_steps);
        Ok(result)
    }

    pub fn get_node_by_full_name(&self, full_name: &str) -> Result<AttackGraphNodeId, GraphError> {
        get_node_by_full_name(&self.full_name_to_node, full_name)
    }

    /// `AttackGraphNode::full_name`: explicit override, else
    /// `"{model asset name}:{step name}"` when `model` resolves the
    /// node's asset, else the `"{id}:{name}"` fallback.
    pub fn full_name_of(&self, key: AttackGraphNodeId, model: Option<&Model>) -> String {
        let node = &self.nodes[key];
        if let Some(explicit) = &node.full_name_override {
            return explicit.clone();
        }
        if let (Some(model), Some(asset_id)) = (model, node.model_asset) {
            if let Some(asset) = model.get_asset_by_id(asset_id) {
                return format!("{}:{}", asset.name, node.name);
            }
        }
        node.fallback_full_name()
    }

    #[allow(clippy::too_many_arguments)]
    pub fn add_node(
        &mut self,
        lg_attack_step: maltoolbox_language::graph::AttackStepId,
        model: Option<&Model>,
        node_id: Option<i64>,
        model_asset: Option<i64>,
        ttc_dist: Option<Value>,
        existence_status: Option<bool>,
        full_name: Option<String>,
    ) -> Result<AttackGraphNodeId, GraphError> {
        let node_id = node_id.unwrap_or(self.next_node_id);
        if self.id_to_node.contains_key(&node_id) {
            return Err(GraphError::DuplicateNodeId(node_id));
        }
        self.next_node_id = node_id + 1;

        let lg_step = self.lang_graph.step(lg_attack_step);
        let node = AttackGraphNode {
            id: node_id,
            lg_attack_step,
            name: lg_step.name.clone(),
            step_type: lg_step.step_type,
            causal_mode: lg_step.causal_mode,
            ttc: ttc_dist.or_else(|| lg_step.ttc.clone()),
            tags: lg_step.tags.clone(),
            additive_model_effects: crate::node::non_empty(
                lg_step.additive_model_effects(&self.lang_graph),
            ),
            subtractive_model_effects: crate::node::non_empty(
                lg_step.subtractive_model_effects(&self.lang_graph),
            ),
            model_asset,
            existence_status,
            children: Default::default(),
            parents: Default::default(),
            extras: Map::new(),
            detectors: HashMap::new(),
            full_name_override: full_name,
        };

        let step_type = node.step_type;
        let computed_full_name = {
            if let Some(explicit) = &node.full_name_override {
                explicit.clone()
            } else if let (Some(model), Some(asset_id)) = (model, model_asset) {
                match model.get_asset_by_id(asset_id) {
                    Some(asset) => format!("{}:{}", asset.name, node.name),
                    None => node.fallback_full_name(),
                }
            } else {
                node.fallback_full_name()
            }
        };

        let key = self.nodes.insert(node);
        self.id_to_node.insert(node_id, key);
        self.full_name_to_node.insert(computed_full_name, key);
        match step_type {
            maltoolbox_language::graph::attack_step::AttackStepType::Or
            | maltoolbox_language::graph::attack_step::AttackStepType::And => {
                self.attack_steps.push(key)
            }
            maltoolbox_language::graph::attack_step::AttackStepType::Defense => {
                self.defense_steps.push(key)
            }
            _ => {}
        }

        Ok(key)
    }

    pub fn remove_node(&mut self, key: AttackGraphNodeId) -> Result<(), GraphError> {
        let (id, children, parents) = {
            let node = &self.nodes[key];
            (node.id, node.children.clone(), node.parents.clone())
        };
        for child in children {
            self.nodes[child].parents.remove(&key);
        }
        for parent in parents {
            self.nodes[parent].children.remove(&key);
        }

        let full_name = self.full_name_to_node.iter().find_map(|(name, &k)| (k == key).then(|| name.clone()));

        self.nodes.remove(key);
        self.id_to_node.remove(&id);
        if let Some(name) = full_name {
            self.full_name_to_node.remove(&name);
        }
        self.attack_steps.retain(|&k| k != key);
        self.defense_steps.retain(|&k| k != key);
        Ok(())
    }

    pub fn to_dict(&self, model: Option<&Model>) -> Value {
        let mut steps = Map::new();
        for key in self.nodes.keys() {
            let full_name = self.full_name_of(key, model);
            steps.insert(full_name, self.node_to_dict(key, model));
        }
        json!({ "attack_steps": steps })
    }

    pub fn save_to_file(
        &self,
        model: Option<&Model>,
        path: impl AsRef<std::path::Path>,
    ) -> Result<(), maltoolbox_fileutil::FileUtilError> {
        maltoolbox_fileutil::save_dict_to_file(path, &self.to_dict(model))
    }

    fn node_to_dict(&self, key: AttackGraphNodeId, model: Option<&Model>) -> Value {
        let node = &self.nodes[key];

        let mut children = Map::new();
        for &child_key in &node.children {
            children.insert(
                self.nodes[child_key].id.to_string(),
                Value::String(self.full_name_of(child_key, model)),
            );
        }
        let mut parents = Map::new();
        for &parent_key in &node.parents {
            parents.insert(
                self.nodes[parent_key].id.to_string(),
                Value::String(self.full_name_of(parent_key, model)),
            );
        }

        let mut dict = json!({
            "id": node.id,
            "type": node.step_type.as_str(),
            "lang_graph_attack_step": self.lang_graph.step(node.lg_attack_step).full_name(&self.lang_graph),
            "name": node.name,
            "ttc": node.ttc,
            "children": children,
            "parents": parents,
        });

        // Python's `Detector.to_dict()` embeds the live `node` and
        // `potential_context` object references directly, which is not
        // actually JSON-serializable - saving a graph with detectors to
        // a file would crash the original. This port serializes name
        // and tprate only, which is what the original's intent clearly
        // was (the rest never round-trips either way).
        if !node.detectors.is_empty() {
            let mut detectors = Map::new();
            for detector in node.detectors.values() {
                let key_name = detector.name.clone().unwrap_or_default();
                detectors.insert(
                    key_name,
                    json!({
                        "name": detector.name,
                        "tprate": detector.tprate,
                    }),
                );
            }
            dict["detectors"] = Value::Object(detectors);
        }
        if let Some(asset_id) = node.model_asset {
            if let Some(model) = model {
                if let Some(asset) = model.get_asset_by_id(asset_id) {
                    dict["asset"] = Value::String(asset.name.clone());
                }
            }
        }
        if let Some(status) = node.existence_status {
            dict["existence_status"] = Value::Bool(status);
        }
        if !node.tags.is_empty() {
            dict["tags"] = Value::Array(node.tags.iter().cloned().map(Value::String).collect());
        }
        if !node.extras.is_empty() {
            dict["extras"] = Value::Object(node.extras.clone());
        }

        dict
    }
}
