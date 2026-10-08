//! Port of `maltoolbox/model.py`.
//!
//! Assets are keyed by their stable, user-facing integer id in a plain
//! `HashMap`, rather than the generational-key arena used by the
//! language/attack graphs - a `Model` has no partial-regeneration churn
//! that would risk a stale reference aliasing a reused slot, so that
//! extra machinery isn't needed here. See `PORTING_NOTES.md` for the
//! full comparison.

use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use serde_json::{json, Map, Value};

use maltoolbox_language::graph::LanguageGraph;

pub const MALTOOLBOX_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Debug, thiserror::Error)]
pub enum ModelError {
    #[error("Asset index {0} already in use.")]
    DuplicateAssetId(i64),
    #[error(
        "Asset type \"{asset_type}\" does not exist in language, must be one of:\n -{available}"
    )]
    UnknownAssetType {
        asset_type: String,
        available: String,
    },
    #[error("Asset name {0} is a duplicate and we do not allow duplicates.")]
    DuplicateAssetName(String),
    #[error("Asset \"{name}\"({id}) is not part of model \"{model}\".")]
    AssetNotFound {
        name: String,
        id: i64,
        model: String,
    },
    #[error("Fieldname '{fieldname}' is not an accepted association fieldname from asset type {asset_type}. Did you mean one of {accepted}?")]
    UnknownFieldname {
        fieldname: String,
        asset_type: String,
        accepted: String,
    },
    #[error("Asset '{asset_name}' of type '{asset_type}' can not be added to association '{owner_name}.{fieldname}'. Expected type of '{fieldname}' is {expected_type}.")]
    WrongAssociatedAssetType {
        asset_name: String,
        asset_type: String,
        owner_name: String,
        fieldname: String,
        expected_type: String,
    },
    #[error("You can have maximum {0} assets for association field {1}")]
    TooManyAssetsInField(i64, String),
    #[error("Association fieldname \"{fieldname}\" does not exist from <{from_type}> to <{to_type}>, must be one of:\n -{possible}")]
    UnknownAssociation {
        fieldname: String,
        from_type: String,
        to_type: String,
        possible: String,
    },
    #[error("Asset with id {0} not found in model.")]
    UnknownAssetId(i64),
    #[error(
        "Asset '{asset_name}' is not associated via fieldname '{fieldname}' on '{owner_name}'."
    )]
    NotAssociated {
        owner_name: String,
        fieldname: String,
        asset_name: String,
    },
    #[error("{0}")]
    Language(#[from] maltoolbox_language::graph::GraphError),
    #[error("{0}")]
    Malformed(String),
}

/// Snapshot of an asset's data at the moment it is removed from the
/// model, letting callers (e.g. `AttackGraph::partially_regenerate_graph`)
/// resolve a removed asset's language type/name without needing
/// `Model::get_asset_by_id` to keep working for its id. Returned by
/// [`Model::remove_asset`].
///
/// `final_state` is captured *after* the associated-assets cleanup loop
/// in [`Model::remove_asset`] has run, so its `associated_assets` field
/// reflects the post-cleanup (typically empty) state, not the
/// pre-removal one.
#[derive(Debug, Clone)]
pub struct AssetSnapshot {
    pub name: String,
    pub lg_asset: maltoolbox_language::graph::AssetId,
    pub final_state: ModelAsset,
}

#[derive(Debug, Clone)]
pub struct ModelAsset {
    pub name: String,
    pub id: i64,
    pub lg_asset: maltoolbox_language::graph::AssetId,
    pub asset_type: String,
    pub defenses: HashMap<String, f64>,
    pub extras: Map<String, Value>,
    pub associated_assets: HashMap<String, HashSet<i64>>,
}

impl ModelAsset {
    pub fn to_dict(&self) -> Value {
        let mut dict = Map::new();
        dict.insert("name".into(), json!(self.name));
        dict.insert("type".into(), json!(self.asset_type));

        if !self.defenses.is_empty() {
            dict.insert("defenses".into(), json!(self.defenses));
        }

        // Filled in by `Model::to_dict`, which has the id->name mapping needed.
        dict.insert("associated_assets".into(), Value::Object(Map::new()));

        if !self.extras.is_empty() {
            dict.insert("extras".into(), Value::Object(self.extras.clone()));
        }

        Value::Object(dict)
    }
}

pub struct Model {
    pub name: String,
    pub maltoolbox_version: String,
    pub next_id: i64,
    pub assets: HashMap<i64, ModelAsset>,
    pub name_to_asset_id: HashMap<String, i64>,
    /// Insertion order of assets. Attack graph generation iterates
    /// assets in this order to assign node ids deterministically, so it
    /// must match Python dict iteration order rather than `HashMap`'s
    /// arbitrary order.
    pub asset_order: Vec<i64>,
    pub lang_graph: Rc<LanguageGraph>,
}

impl Model {
    pub fn new(name: impl Into<String>, lang_graph: Rc<LanguageGraph>) -> Self {
        Model {
            name: name.into(),
            maltoolbox_version: MALTOOLBOX_VERSION.to_string(),
            next_id: 0,
            assets: HashMap::new(),
            name_to_asset_id: HashMap::new(),
            asset_order: Vec::new(),
            lang_graph,
        }
    }

    #[allow(clippy::too_many_arguments)]
    pub fn add_asset(
        &mut self,
        asset_type: &str,
        name: Option<String>,
        asset_id: Option<i64>,
        defenses: Option<HashMap<String, f64>>,
        extras: Option<Map<String, Value>>,
        allow_duplicate_names: bool,
    ) -> Result<i64, ModelError> {
        let asset_id = asset_id.unwrap_or(self.next_id);
        if self.assets.contains_key(&asset_id) {
            return Err(ModelError::DuplicateAssetId(asset_id));
        }
        self.next_id = self.next_id.max(asset_id + 1);

        let name = match name {
            None => format!("{asset_type}:{asset_id}"),
            Some(n) if self.name_to_asset_id.contains_key(&n) => {
                if allow_duplicate_names {
                    format!("{n}:{asset_id}")
                } else {
                    return Err(ModelError::DuplicateAssetName(n));
                }
            }
            Some(n) => n,
        };

        let lg_asset =
            self.lang_graph
                .asset_id(asset_type)
                .ok_or_else(|| ModelError::UnknownAssetType {
                    asset_type: asset_type.to_string(),
                    available: self
                        .lang_graph
                        .asset_order
                        .iter()
                        .map(|id| self.lang_graph.asset(*id).name.as_str())
                        .collect::<Vec<_>>()
                        .join("\n -"),
                })?;

        let asset = ModelAsset {
            name: name.clone(),
            id: asset_id,
            lg_asset,
            asset_type: asset_type.to_string(),
            defenses: defenses.unwrap_or_default(),
            extras: extras.unwrap_or_default(),
            associated_assets: HashMap::new(),
        };

        self.assets.insert(asset_id, asset);
        self.name_to_asset_id.insert(name, asset_id);
        self.asset_order.push(asset_id);

        Ok(asset_id)
    }

    pub fn remove_asset(&mut self, asset_id: i64) -> Result<AssetSnapshot, ModelError> {
        let asset = self
            .assets
            .get(&asset_id)
            .ok_or_else(|| ModelError::AssetNotFound {
                name: String::new(),
                id: asset_id,
                model: self.name.clone(),
            })?;
        let name = asset.name.clone();
        let lg_asset = asset.lg_asset;

        let associated_fieldnames: Vec<(String, HashSet<i64>)> = asset
            .associated_assets
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();
        for (fieldname, assoc_assets) in associated_fieldnames {
            self.remove_associated_assets(asset_id, &fieldname, &assoc_assets)?;
        }

        // Captured after the cleanup loop above, so `associated_assets` is already emptied.
        let final_state = self
            .assets
            .get(&asset_id)
            .expect("asset confirmed present above, not removed by cleanup loop")
            .clone();
        let snapshot = AssetSnapshot {
            name,
            lg_asset,
            final_state,
        };

        self.assets.remove(&asset_id);
        self.name_to_asset_id.remove(&snapshot.name);
        self.asset_order.retain(|&id| id != asset_id);
        Ok(snapshot)
    }

    pub fn get_asset_by_id(&self, asset_id: i64) -> Option<&ModelAsset> {
        self.assets.get(&asset_id)
    }

    pub fn get_asset_by_name(&self, name: &str) -> Option<&ModelAsset> {
        self.name_to_asset_id
            .get(name)
            .and_then(|id| self.assets.get(id))
    }

    pub fn associations_with(
        &self,
        asset_id: i64,
        other_id: i64,
    ) -> HashSet<Rc<maltoolbox_language::graph::LanguageGraphAssociation>> {
        let Some(asset) = self.assets.get(&asset_id) else {
            return HashSet::new();
        };
        let mut result = HashSet::new();
        for assoc in self.lang_graph.associations(asset.lg_asset).values() {
            let to_left = asset
                .associated_assets
                .get(&assoc.left_field.fieldname)
                .map(|s| s.contains(&other_id))
                .unwrap_or(false);
            let to_right = asset
                .associated_assets
                .get(&assoc.right_field.fieldname)
                .map(|s| s.contains(&other_id))
                .unwrap_or(false);
            if to_left || to_right {
                result.insert(assoc.clone());
            }
        }
        result
    }

    pub fn has_association_with(&self, asset_id: i64, other_id: i64, assoc_name: &str) -> bool {
        let Some(asset) = self.assets.get(&asset_id) else {
            return false;
        };
        for (fieldname, assoc_assets) in &asset.associated_assets {
            let Some(assoc) = self
                .lang_graph
                .associations(asset.lg_asset)
                .get(fieldname)
                .cloned()
            else {
                continue;
            };
            if assoc.name == assoc_name && assoc_assets.contains(&other_id) {
                return true;
            }
        }
        false
    }

    pub fn validate_associated_assets(
        &self,
        asset_id: i64,
        fieldname: &str,
        assets_to_add: &HashSet<i64>,
    ) -> Result<(), ModelError> {
        let asset = self.assets.get(&asset_id).expect("asset must exist");
        let associations = self.lang_graph.associations(asset.lg_asset);

        let Some(lg_assoc) = associations.get(fieldname) else {
            return Err(ModelError::UnknownFieldname {
                fieldname: fieldname.to_string(),
                asset_type: self.lang_graph.asset(asset.lg_asset).name.clone(),
                accepted: associations.keys().cloned().collect::<Vec<_>>().join(", "),
            });
        };
        let assoc_field = lg_assoc.get_field(fieldname);

        for &other_id in assets_to_add {
            let other = self.assets.get(&other_id).expect("asset must exist");
            if !self
                .lang_graph
                .is_subasset_of(other.lg_asset, assoc_field.asset)
            {
                return Err(ModelError::WrongAssociatedAssetType {
                    asset_name: other.name.clone(),
                    asset_type: other.asset_type.clone(),
                    owner_name: asset.name.clone(),
                    fieldname: fieldname.to_string(),
                    expected_type: self.lang_graph.asset(assoc_field.asset).name.clone(),
                });
            }
        }

        let before = asset
            .associated_assets
            .get(fieldname)
            .cloned()
            .unwrap_or_default();
        let after_len = before.union(assets_to_add).count();
        if let Some(max) = assoc_field.maximum {
            if after_len as i64 > max {
                return Err(ModelError::TooManyAssetsInField(max, fieldname.to_string()));
            }
        }

        Ok(())
    }

    pub fn add_associated_assets(
        &mut self,
        asset_id: i64,
        fieldname: &str,
        assets: HashSet<i64>,
    ) -> Result<(), ModelError> {
        let asset = self.assets.get(&asset_id).expect("asset must exist");
        let associations = self.lang_graph.associations(asset.lg_asset);

        let Some(lg_assoc) = associations.get(fieldname).cloned() else {
            let (to_asset_type, possible): (String, Vec<String>) =
                if let Some(&first_other) = assets.iter().next() {
                    let other_lg_asset = self.assets[&first_other].lg_asset;
                    let to_name = self.lang_graph.asset(other_lg_asset).name.clone();
                    let possible = self
                        .lang_graph
                        .associations_to(asset.lg_asset, other_lg_asset)
                        .keys()
                        .cloned()
                        .collect();
                    (to_name, possible)
                } else {
                    ("Any".to_string(), associations.keys().cloned().collect())
                };
            return Err(ModelError::UnknownAssociation {
                fieldname: fieldname.to_string(),
                from_type: self.lang_graph.asset(asset.lg_asset).name.clone(),
                to_type: to_asset_type,
                possible: possible.join("\n -"),
            });
        };
        let other_fieldname = lg_assoc.get_opposite_fieldname(fieldname)?;

        self.validate_associated_assets(asset_id, fieldname, &assets)?;
        for &other_id in &assets {
            self.validate_associated_assets(
                other_id,
                &other_fieldname,
                &HashSet::from([asset_id]),
            )?;
        }

        self.assets
            .get_mut(&asset_id)
            .unwrap()
            .associated_assets
            .entry(fieldname.to_string())
            .or_default()
            .extend(&assets);

        for &other_id in &assets {
            self.assets
                .get_mut(&other_id)
                .unwrap()
                .associated_assets
                .entry(other_fieldname.clone())
                .or_default()
                .insert(asset_id);
        }

        Ok(())
    }

    pub fn remove_associated_assets(
        &mut self,
        asset_id: i64,
        fieldname: &str,
        assets: &HashSet<i64>,
    ) -> Result<(), ModelError> {
        let asset = self
            .assets
            .get(&asset_id)
            .ok_or(ModelError::UnknownAssetId(asset_id))?;
        let lg_assoc = self
            .lang_graph
            .associations(asset.lg_asset)
            .get(fieldname)
            .cloned()
            .ok_or_else(|| ModelError::UnknownFieldname {
                fieldname: fieldname.to_string(),
                asset_type: self.lang_graph.asset(asset.lg_asset).name.clone(),
                accepted: self
                    .lang_graph
                    .associations(asset.lg_asset)
                    .keys()
                    .cloned()
                    .collect::<Vec<_>>()
                    .join(", "),
            })?;
        let owner_name = asset.name.clone();
        let other_fieldname = lg_assoc.get_opposite_fieldname(fieldname)?;

        for &other_id in assets {
            let other = self
                .assets
                .get_mut(&other_id)
                .ok_or(ModelError::UnknownAssetId(other_id))?;
            let is_associated = other
                .associated_assets
                .get(&other_fieldname)
                .map(|set| set.contains(&asset_id))
                .unwrap_or(false);
            if !is_associated {
                return Err(ModelError::NotAssociated {
                    owner_name: other.name.clone(),
                    fieldname: other_fieldname,
                    asset_name: owner_name,
                });
            }

            let set = other.associated_assets.get_mut(&other_fieldname).unwrap();
            set.remove(&asset_id);
            if set.is_empty() {
                other.associated_assets.remove(&other_fieldname);
            }
        }

        let this = self.assets.get_mut(&asset_id).unwrap();
        if let Some(set) = this.associated_assets.get_mut(fieldname) {
            for id in assets {
                set.remove(id);
            }
            if set.is_empty() {
                this.associated_assets.remove(fieldname);
            }
        }

        Ok(())
    }

    pub fn to_dict(&self) -> Value {
        let mut assets = Map::new();
        for (id, asset) in &self.assets {
            let mut dict = asset.to_dict();
            let mut associated_assets = Map::new();
            for (fieldname, ids) in &asset.associated_assets {
                let mut named = Map::new();
                for other_id in ids {
                    let other_name = self.assets[other_id].name.clone();
                    named.insert(other_id.to_string(), json!(other_name));
                }
                associated_assets.insert(fieldname.clone(), Value::Object(named));
            }
            dict["associated_assets"] = Value::Object(associated_assets);
            assets.insert(id.to_string(), dict);
        }

        json!({
            "metadata": {
                "name": self.name,
                "langVersion": self.lang_graph.metadata.version,
                "langID": self.lang_graph.metadata.id,
                "malVersion": "0.1.0-SNAPSHOT",
                "MAL-Toolbox Version": self.maltoolbox_version,
                "info": "Created by the mal-toolbox model python module.",
            },
            "assets": assets,
        })
    }
}
