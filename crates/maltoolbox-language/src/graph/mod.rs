//! Port of mal-toolbox's `maltoolbox/language/languagegraph.py` and
//! supporting modules: a graph representation of a compiled MAL language,
//! built from the `langspec` JSON produced by [`crate::compiler`].

pub mod asset;
pub mod assoc;
pub mod assoc_traversal;
pub mod attack_step;
pub mod builder;
pub mod detector;
pub mod expr_chain;
pub mod file;
pub mod ids;
pub mod lookup;
pub mod model_effect;
pub mod step_expr;

use std::collections::{HashMap, HashSet};

use indexmap::IndexMap;
use serde_json::{json, Value};
use slotmap::SlotMap;

pub use asset::LanguageGraphAsset;
pub use assoc::{LanguageGraphAssociation, LanguageGraphAssociationField};
pub use attack_step::LanguageGraphAttackStep;
pub use detector::{LanguageGraphContextItem, LanguageGraphDetector};
pub use expr_chain::{ExprType, ExpressionsChain};
pub use ids::{AssetId, AttackStepId};

#[derive(Debug, thiserror::Error)]
pub enum GraphError {
    #[error("{0}")]
    Malformed(String),
    #[error("super asset \"{super_name}\" for asset \"{asset_name}\" not found")]
    SuperAssetNotFound {
        asset_name: String,
        super_name: String,
    },
    #[error("left asset \"{asset_name}\" for association \"{assoc_name}\" not found")]
    AssociationAssetNotFound {
        assoc_name: String,
        asset_name: String,
    },
    #[error("failed to find target asset for step expression:\n{0}")]
    StepExpression(String),
    #[error("{0}")]
    Lookup(String),
}

#[derive(Debug, Clone, Default)]
pub struct Metadata {
    pub version: String,
    pub id: String,
}

/// `Clone` added for `maltoolbox-model-py`'s `PyModel`: the core
/// `maltoolbox_model::Model` needs a bare `Rc<LanguageGraph>` (no
/// `RefCell`), but the PyO3 `PyLanguageGraph` wraps `Rc<RefCell<
/// LanguageGraph>>` (so `regenerate_graph` can mutate it) - the two
/// don't compose without copying the data once. See
/// PYTHON_BINDINGS_IMPLEMENTATION.md's Phase 2 status for the narrow,
/// confirmed-unused-in-practice divergence this introduces
/// (`regenerate_graph` on the original `LanguageGraph` object isn't
/// reflected in a `Model` already built from it).
#[derive(Clone)]
pub struct LanguageGraph {
    pub assets: SlotMap<AssetId, LanguageGraphAsset>,
    pub steps: SlotMap<AttackStepId, LanguageGraphAttackStep>,
    pub asset_id_by_name: HashMap<String, AssetId>,
    /// Insertion order of assets, mirroring Python dict iteration order
    /// over `lang_spec['assets']` - needed because some builder passes
    /// (e.g. `_inherit_attack_steps`'s deferral loop) are order-sensitive.
    pub asset_order: Vec<AssetId>,
    pub metadata: Metadata,
    pub lang_spec: Value,
}

impl LanguageGraph {
    pub fn asset(&self, id: AssetId) -> &LanguageGraphAsset {
        &self.assets[id]
    }

    pub fn step(&self, id: AttackStepId) -> &LanguageGraphAttackStep {
        &self.steps[id]
    }

    pub fn asset_id(&self, name: &str) -> Option<AssetId> {
        self.asset_id_by_name.get(name).copied()
    }

    pub fn is_subasset_of(&self, asset: AssetId, target: AssetId) -> bool {
        let mut current = Some(asset);
        while let Some(id) = current {
            if id == target {
                return true;
            }
            current = self.asset(id).own_super_asset;
        }
        false
    }

    /// This asset plus every asset that directly or indirectly extends it.
    pub fn sub_assets(&self, asset: AssetId) -> HashSet<AssetId> {
        let mut result = HashSet::new();
        result.insert(asset);
        for &child in &self.asset(asset).own_sub_assets {
            result.extend(self.sub_assets(child));
        }
        result
    }

    /// This asset plus every asset it directly or indirectly extends,
    /// closest ancestor first.
    pub fn super_assets(&self, asset: AssetId) -> Vec<AssetId> {
        let mut result = Vec::new();
        let mut current = Some(asset);
        while let Some(id) = current {
            result.push(id);
            current = self.asset(id).own_super_asset;
        }
        result
    }

    /// Own + inherited associations (`LanguageGraphAsset.associations`).
    /// `IndexMap` to preserve insertion order from `own_associations`
    /// (Phase 4 decision 7) - this feeds step-expression association
    /// resolution (`step_expr.rs`) and is exposed to Python callers as
    /// ordered dict-like iteration.
    pub fn associations(
        &self,
        asset: AssetId,
    ) -> IndexMap<String, std::rc::Rc<LanguageGraphAssociation>> {
        let mut result: IndexMap<String, std::rc::Rc<LanguageGraphAssociation>> = IndexMap::new();
        if let Some(super_asset) = self.asset(asset).own_super_asset {
            result.extend(self.associations(super_asset));
        }
        for (k, v) in &self.asset(asset).own_associations {
            result.insert(k.clone(), v.clone());
        }
        result
    }

    /// Own + inherited variables (`LanguageGraphAsset.variables`).
    pub fn variables(
        &self,
        asset: AssetId,
    ) -> IndexMap<String, (AssetId, Option<ExpressionsChain>)> {
        let mut result: IndexMap<String, (AssetId, Option<ExpressionsChain>)> = IndexMap::new();
        if let Some(super_asset) = self.asset(asset).own_super_asset {
            result.extend(self.variables(super_asset));
        }
        for (k, v) in &self.asset(asset).own_variables {
            result.insert(k.clone(), v.clone());
        }
        result
    }

    /// Associations on `asset` that also appear on `asset_type`
    /// (`LanguageGraphAsset.associations_to`).
    pub fn associations_to(
        &self,
        asset: AssetId,
        asset_type: AssetId,
    ) -> IndexMap<String, std::rc::Rc<LanguageGraphAssociation>> {
        let target_assocs: Vec<_> = self.associations(asset_type).into_values().collect();
        self.associations(asset)
            .into_iter()
            .filter(|(_, assoc)| target_assocs.iter().any(|a| std::rc::Rc::ptr_eq(a, assoc)))
            .collect()
    }

    pub fn get_all_common_superassets(&self, a: AssetId, b: AssetId) -> HashSet<String> {
        let self_names: HashSet<String> = self
            .super_assets(a)
            .iter()
            .map(|id| self.asset(*id).name.clone())
            .collect();
        let other_names: HashSet<String> = self
            .super_assets(b)
            .iter()
            .map(|id| self.asset(*id).name.clone())
            .collect();
        self_names.intersection(&other_names).cloned().collect()
    }

    /// Maps each association fieldname to the `(asset_type, attack_step_name)`
    /// pairs whose children expression chains can traverse that field.
    /// Computed fresh each call (the Python original caches it as a
    /// `cached_property`; not performance-critical enough here to
    /// justify the extra bookkeeping of invalidating a cache on graph
    /// mutation).
    pub fn fieldname_to_candidate_steps(&self) -> HashMap<String, HashSet<(String, String)>> {
        let mut mapping: HashMap<String, HashSet<(String, String)>> = HashMap::new();
        for &asset_id in &self.asset_order {
            let asset = self.asset(asset_id);
            for &step_id in asset.attack_steps.values() {
                let step = self.step(step_id);
                let mut fieldnames: HashSet<String> = HashSet::new();
                for chains in step.children(self).values() {
                    for chain in chains {
                        fieldnames.extend(expr_chain::chain_fieldnames(chain.as_ref()));
                    }
                }
                for fieldname in fieldnames {
                    mapping
                        .entry(fieldname)
                        .or_default()
                        .insert((asset.name.clone(), step.name.clone()));
                }
            }
        }
        mapping
    }
}

/// Build a [`LanguageGraph`] from a compiled langspec (see
/// [`crate::compiler::compile_file`]).
pub fn generate_graph(lang_spec: Value) -> Result<LanguageGraph, GraphError> {
    let metadata = Metadata {
        version: lang_spec["defines"]["version"]
            .as_str()
            .unwrap_or_default()
            .to_string(),
        id: lang_spec["defines"]["id"]
            .as_str()
            .unwrap_or_default()
            .to_string(),
    };

    let mut graph = LanguageGraph {
        assets: SlotMap::with_key(),
        steps: SlotMap::with_key(),
        asset_id_by_name: HashMap::new(),
        asset_order: Vec::new(),
        metadata,
        lang_spec,
    };

    builder::generate_graph(&mut graph)?;
    Ok(graph)
}

pub fn language_graph_to_dict(graph: &LanguageGraph) -> Result<Value, GraphError> {
    let mut serialized = serde_json::Map::new();
    serialized.insert(
        "metadata".to_string(),
        json!({ "version": graph.metadata.version, "id": graph.metadata.id }),
    );
    for &asset_id in &graph.asset_order {
        let asset = graph.asset(asset_id);
        serialized.insert(asset.name.clone(), asset.to_dict(graph)?);
    }
    Ok(Value::Object(serialized))
}
