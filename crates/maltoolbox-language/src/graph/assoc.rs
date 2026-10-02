//! Port of `maltoolbox/language/language_graph_assoc.py`.

use std::collections::HashMap;

use super::ids::AssetId;
use super::{GraphError, LanguageGraph};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct LanguageGraphAssociationField {
    pub asset: AssetId,
    pub fieldname: String,
    pub minimum: i64,
    pub maximum: Option<i64>,
}

/// `info` is deliberately excluded from `PartialEq`/`Hash`, mirroring the
/// Python dataclass's `field(default_factory=dict, compare=False)` -
/// metadata doesn't affect association identity.
#[derive(Debug, Clone)]
pub struct LanguageGraphAssociation {
    pub name: String,
    pub left_field: LanguageGraphAssociationField,
    pub right_field: LanguageGraphAssociationField,
    pub info: HashMap<String, String>,
}

impl PartialEq for LanguageGraphAssociation {
    fn eq(&self, other: &Self) -> bool {
        self.name == other.name
            && self.left_field == other.left_field
            && self.right_field == other.right_field
    }
}

impl Eq for LanguageGraphAssociation {}

impl std::hash::Hash for LanguageGraphAssociation {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.name.hash(state);
        self.left_field.hash(state);
        self.right_field.hash(state);
    }
}

impl LanguageGraphAssociation {
    pub fn full_name(&self) -> String {
        format!(
            "{}_{}_{}",
            self.name, self.left_field.fieldname, self.right_field.fieldname
        )
    }

    pub fn get_field(&self, fieldname: &str) -> &LanguageGraphAssociationField {
        if self.right_field.fieldname == fieldname {
            &self.right_field
        } else {
            &self.left_field
        }
    }

    pub fn contains_fieldname(&self, fieldname: &str) -> bool {
        self.left_field.fieldname == fieldname || self.right_field.fieldname == fieldname
    }

    pub fn contains_asset(&self, graph: &LanguageGraph, asset: AssetId) -> bool {
        graph.is_subasset_of(asset, self.left_field.asset)
            || graph.is_subasset_of(asset, self.right_field.asset)
    }

    pub fn get_opposite_fieldname(&self, fieldname: &str) -> Result<String, GraphError> {
        if self.left_field.fieldname == fieldname {
            return Ok(self.right_field.fieldname.clone());
        }
        if self.right_field.fieldname == fieldname {
            return Ok(self.left_field.fieldname.clone());
        }
        Err(GraphError::Malformed(format!(
            "Requested fieldname \"{fieldname}\" from association {} which did not contain it!",
            self.name
        )))
    }

    pub fn resolve_field_asset_type(
        &self,
        graph: &LanguageGraph,
        fieldname: &str,
    ) -> Result<String, GraphError> {
        if fieldname == self.left_field.fieldname {
            return Ok(graph.asset(self.left_field.asset).name.clone());
        }
        if fieldname == self.right_field.fieldname {
            return Ok(graph.asset(self.right_field.asset).name.clone());
        }
        Err(GraphError::Malformed(format!(
            "Field \"{fieldname}\" not found in association {}",
            self.name
        )))
    }

    pub fn to_dict(&self, graph: &LanguageGraph) -> serde_json::Value {
        serde_json::json!({
            "name": self.name,
            "info": self.info,
            "left": {
                "asset": graph.asset(self.left_field.asset).name.clone(),
                "fieldname": self.left_field.fieldname,
                "min": self.left_field.minimum,
                "max": self.left_field.maximum,
            },
            "right": {
                "asset": graph.asset(self.right_field.asset).name.clone(),
                "fieldname": self.right_field.fieldname,
                "min": self.right_field.minimum,
                "max": self.right_field.maximum,
            },
        })
    }
}
