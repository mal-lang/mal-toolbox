//! Port of `Model._from_dict`/`Model.load_from_file`/`Model.save_to_file`
//! (the file-I/O parts of `maltoolbox/model.py`).

use std::collections::HashMap;
use std::path::Path;
use std::rc::Rc;

use maltoolbox_language::graph::LanguageGraph;
use serde_json::Value;

use crate::model::{Model, ModelError};

#[derive(Debug, thiserror::Error)]
pub enum LoadError {
    #[error("{0}")]
    FileUtil(#[from] maltoolbox_fileutil::FileUtilError),
    #[error("{0}")]
    Model(#[from] ModelError),
    #[error("Could not load model. It might be of an older version. Try to upgrade it with 'maltoolbox upgrade-model': {0}")]
    Malformed(String),
}

pub fn save_to_file(
    model: &Model,
    path: impl AsRef<Path>,
) -> Result<(), maltoolbox_fileutil::FileUtilError> {
    maltoolbox_fileutil::save_dict_to_file(path, &model.to_dict())
}

pub fn load_from_file(
    path: impl AsRef<Path>,
    lang_graph: Rc<LanguageGraph>,
) -> Result<Model, LoadError> {
    let dict = maltoolbox_fileutil::load_dict_from_file(path)?;
    from_dict(&dict, lang_graph).map_err(|e| LoadError::Malformed(e.to_string()))
}

/// Port of `Model._from_dict`.
///
/// Reads the `"MAL-Toolbox Version"` (hyphenated) metadata key, matching
/// what `to_dict` (`model.rs`) writes; see `PORTING_NOTES.md` for why
/// this diverges from the Python original.
pub fn from_dict(serialized: &Value, lang_graph: Rc<LanguageGraph>) -> Result<Model, LoadError> {
    let metadata = &serialized["metadata"];
    let name = metadata["name"]
        .as_str()
        .ok_or_else(|| LoadError::Malformed("metadata.name missing".into()))?;
    let maltoolbox_version = metadata["MAL-Toolbox Version"]
        .as_str()
        .unwrap_or(crate::model::MALTOOLBOX_VERSION)
        .to_string();

    let mut model = Model::new(name, lang_graph);
    model.maltoolbox_version = maltoolbox_version;

    let assets = serialized["assets"]
        .as_object()
        .ok_or_else(|| LoadError::Malformed("assets missing".into()))?;

    for (asset_id, asset_value) in assets {
        let id: i64 = asset_id
            .parse()
            .map_err(|_| LoadError::Malformed(format!("invalid asset id \"{asset_id}\"")))?;

        // An asset may be given as a bare type-name string instead of an object.
        let (asset_type, name, defenses_raw, extras) = match asset_value {
            Value::Object(obj) => (
                obj["type"].as_str().unwrap_or_default().to_string(),
                obj["name"].as_str().unwrap_or_default().to_string(),
                obj.get("defenses").cloned(),
                obj.get("extras").and_then(Value::as_object).cloned(),
            ),
            Value::String(s) => (s.clone(), format!("{s}:{asset_id}"), None, None),
            _ => {
                return Err(LoadError::Malformed(format!(
                    "asset {asset_id} must be an object or a type-name string"
                )))
            }
        };

        // Defense values may be JSON numbers or numeric strings (older
        // model versions serialize them as strings); accept either.
        let defenses: HashMap<String, f64> = defenses_raw
            .and_then(|d| d.as_object().cloned())
            .into_iter()
            .flatten()
            .filter_map(|(k, v)| {
                v.as_f64()
                    .or_else(|| v.as_str().and_then(|s| s.parse().ok()))
                    .map(|f| (k, f))
            })
            .collect();

        model
            .add_asset(
                &asset_type,
                Some(name),
                Some(id),
                Some(defenses),
                extras,
                true,
            )
            .map_err(LoadError::Model)?;
    }

    for (asset_id, asset_value) in assets {
        let id: i64 = asset_id.parse().expect("validated above");
        let Some(associated) = asset_value
            .get("associated_assets")
            .and_then(Value::as_object)
        else {
            continue;
        };
        for (fieldname, assoc_assets) in associated {
            let ids: std::collections::HashSet<i64> = assoc_assets
                .as_object()
                .into_iter()
                .flatten()
                .filter_map(|(k, _)| k.parse().ok())
                .collect();
            model
                .add_associated_assets(id, fieldname, ids)
                .map_err(LoadError::Model)?;
        }
    }

    Ok(model)
}
