//! Port of `maltoolbox/attackgraph/node_getters.py`, plus the
//! `levenshtein_distance` helper from `maltoolbox/str_utils.py` (inlined
//! here since it has no other caller in this crate).

use indexmap::IndexMap;

use crate::ids::AttackGraphNodeId;
use crate::GraphError;

fn levenshtein_distance(a: &str, b: &str) -> usize {
    if a == b {
        return 0;
    }
    if a.is_empty() {
        return b.chars().count();
    }
    if b.is_empty() {
        return a.chars().count();
    }

    let b_chars: Vec<char> = b.chars().collect();
    let mut prev_row: Vec<usize> = (0..=b_chars.len()).collect();

    for ca in a.chars() {
        let mut curr_row = vec![prev_row[0] + 1];
        for (j, &cb) in b_chars.iter().enumerate() {
            let insertions = prev_row[j + 1] + 1;
            let deletions = curr_row[j] + 1;
            let substitutions = prev_row[j] + usize::from(ca != cb);
            curr_row.push(insertions.min(deletions).min(substitutions));
        }
        prev_row = curr_row;
    }

    *prev_row.last().unwrap()
}

pub fn get_similar_full_names(
    full_name_to_node: &IndexMap<String, AttackGraphNodeId>,
    query: &str,
) -> Vec<String> {
    let mut shortest_dist = 100usize;
    let mut similar_names = Vec::new();

    for full_name in full_name_to_node.keys() {
        let dist = levenshtein_distance(query, full_name);
        if dist == shortest_dist {
            similar_names.push(full_name.clone());
        } else if dist < shortest_dist {
            similar_names = vec![full_name.clone()];
            shortest_dist = dist;
        }
    }

    similar_names
}

pub fn get_node_by_full_name(
    full_name_to_node: &IndexMap<String, AttackGraphNodeId>,
    full_name: &str,
) -> Result<AttackGraphNodeId, GraphError> {
    full_name_to_node.get(full_name).copied().ok_or_else(|| {
        let similar_names = get_similar_full_names(full_name_to_node, full_name);
        GraphError::Malformed(format!(
            "Could not find node with name \"{full_name}\". Did you mean: {}?",
            similar_names.join(", ")
        ))
    })
}
