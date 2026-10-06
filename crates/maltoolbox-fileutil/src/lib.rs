//! Port of `maltoolbox/file_utils.py`'s JSON/YAML (de)serialization
//! helpers, used by every crate that saves/loads a dict-shaped value
//! (`LanguageGraph`, `Model`, `AttackGraph`) to/from a file, dispatching
//! on the file extension.

use std::fs;
use std::path::Path;

use serde_json::Value;

#[derive(Debug, thiserror::Error)]
pub enum FileUtilError {
    #[error("failed to read '{path}': {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    #[error("failed to parse JSON in '{path}': {source}")]
    Json {
        path: String,
        #[source]
        source: serde_json::Error,
    },
    #[error("failed to parse YAML in '{path}': {source}")]
    Yaml {
        path: String,
        #[source]
        source: serde_yaml::Error,
    },
    #[error("Unknown file extension, expected json/yml/yaml")]
    UnknownExtension,
}

pub fn save_dict_to_json_file(
    filename: impl AsRef<Path>,
    value: &Value,
) -> Result<(), FileUtilError> {
    let path = filename.as_ref();
    let json = serde_json::to_string_pretty(value).expect("Value serialization cannot fail");
    fs::write(path, json).map_err(|e| FileUtilError::Io {
        path: path.display().to_string(),
        source: e,
    })
}

pub fn save_dict_to_yaml_file(
    filename: impl AsRef<Path>,
    value: &Value,
) -> Result<(), FileUtilError> {
    let path = filename.as_ref();
    let yaml = serde_yaml::to_string(value).expect("Value serialization cannot fail");
    fs::write(path, yaml).map_err(|e| FileUtilError::Io {
        path: path.display().to_string(),
        source: e,
    })
}

/// Save `value` to JSON or YAML depending on `filename`'s extension.
pub fn save_dict_to_file(filename: impl AsRef<Path>, value: &Value) -> Result<(), FileUtilError> {
    let path = filename.as_ref();
    match path.extension().and_then(|e| e.to_str()) {
        Some("yml") | Some("yaml") => save_dict_to_yaml_file(path, value),
        Some("json") => save_dict_to_json_file(path, value),
        _ => Err(FileUtilError::UnknownExtension),
    }
}

pub fn load_dict_from_json_file(filename: impl AsRef<Path>) -> Result<Value, FileUtilError> {
    let path = filename.as_ref();
    let text = fs::read_to_string(path).map_err(|e| FileUtilError::Io {
        path: path.display().to_string(),
        source: e,
    })?;
    serde_json::from_str(&text).map_err(|e| FileUtilError::Json {
        path: path.display().to_string(),
        source: e,
    })
}

pub fn load_dict_from_yaml_file(filename: impl AsRef<Path>) -> Result<Value, FileUtilError> {
    let path = filename.as_ref();
    let text = fs::read_to_string(path).map_err(|e| FileUtilError::Io {
        path: path.display().to_string(),
        source: e,
    })?;
    serde_yaml::from_str(&text).map_err(|e| FileUtilError::Yaml {
        path: path.display().to_string(),
        source: e,
    })
}

/// Load a dict-shaped value from JSON or YAML depending on `filename`'s
/// extension.
pub fn load_dict_from_file(filename: impl AsRef<Path>) -> Result<Value, FileUtilError> {
    let path = filename.as_ref();
    match path.extension().and_then(|e| e.to_str()) {
        Some("yml") | Some("yaml") => load_dict_from_yaml_file(path),
        Some("json") => load_dict_from_json_file(path),
        _ => Err(FileUtilError::UnknownExtension),
    }
}
