//! Port of `maltoolbox/attackgraph/detector.py`.

use std::collections::{HashMap, HashSet};

use crate::ids::AttackGraphNodeId;

#[derive(Debug, Clone, PartialEq)]
pub struct Detector {
    pub name: Option<String>,
    pub node: AttackGraphNodeId,
    pub potential_context: HashMap<String, HashSet<AttackGraphNodeId>>,
    pub tprate: Option<f64>,
    pub fprate: Option<f64>,
}
