//! Port of mal-toolbox's `maltoolbox/patternfinder/attackgraph_patterns.py`:
//! finds sequences of attack graph nodes matching a list of conditions,
//! following `children` edges, with support for optional/repeatable
//! conditions.

use std::collections::HashSet;

use maltoolbox_attackgraph::{AttackGraph, AttackGraphNode, AttackGraphNodeId};

/// A condition that has to be true for a node to match.
///
/// Unlike the Python `@dataclass(frozen=True, eq=True)`, this doesn't
/// derive `PartialEq`/`Hash` - `matches` is a closure, and Python's own
/// dataclass equality over a `Callable` field is really just identity
/// comparison in practice (two different lambdas are never `==`), so
/// there's no meaningful value-equality to preserve here.
pub struct SearchCondition {
    pub matches: Box<dyn Fn(&AttackGraphNode) -> bool>,
    pub greedy: bool,
    pub min_repeated: usize,
    pub max_repeated: usize,
}

impl SearchCondition {
    /// Matches any node unconditionally.
    pub fn any() -> Self {
        SearchCondition {
            matches: Box::new(|_| true),
            greedy: false,
            min_repeated: 1,
            max_repeated: 1,
        }
    }

    pub fn new(matches: impl Fn(&AttackGraphNode) -> bool + 'static) -> Self {
        SearchCondition {
            matches: Box::new(matches),
            greedy: false,
            min_repeated: 1,
            max_repeated: 1,
        }
    }

    pub fn repeated(mut self, min_repeated: usize, max_repeated: usize) -> Self {
        self.min_repeated = min_repeated;
        self.max_repeated = max_repeated;
        self
    }

    pub fn greedy(mut self, greedy: bool) -> Self {
        self.greedy = greedy;
        self
    }

    /// True if this condition can be matched again (another repetition).
    pub fn can_match_again(&self, num_matches: usize) -> bool {
        num_matches < self.max_repeated
    }

    /// True if this condition must match again to be fulfilled.
    pub fn must_match_again(&self, num_matches: usize) -> bool {
        num_matches < self.min_repeated
    }
}

/// A pattern consists of conditions; the conditions are used to find all
/// matching sequences of nodes in an [`AttackGraph`].
pub struct SearchPattern {
    pub conditions: Vec<SearchCondition>,
}

impl SearchPattern {
    pub fn new(conditions: Vec<SearchCondition>) -> Self {
        assert!(!conditions.is_empty(), "a search pattern needs at least one condition");
        SearchPattern { conditions }
    }

    /// Search `graph` for this pattern and return the matching paths of
    /// node ids.
    pub fn find_matches(&self, graph: &AttackGraph) -> Vec<Vec<AttackGraphNodeId>> {
        let first = &self.conditions[0];
        let mut matching_paths: HashSet<Vec<AttackGraphNodeId>> = HashSet::new();

        for node_key in graph.nodes.keys() {
            if (first.matches)(&graph.nodes[node_key]) {
                find_matches_recursively(
                    graph,
                    node_key,
                    &self.conditions,
                    &[],
                    &mut matching_paths,
                    0,
                );
            }
        }

        matching_paths.into_iter().collect()
    }
}

/// Find all paths of nodes that match `conditions`, recursively,
/// following children edges. See the Python original's docstring for
/// the full algorithm description; this is a direct structural port.
fn find_matches_recursively(
    graph: &AttackGraph,
    node: AttackGraphNodeId,
    conditions: &[SearchCondition],
    current_path: &[AttackGraphNodeId],
    matching_paths: &mut HashSet<Vec<AttackGraphNodeId>>,
    condition_match_count: usize,
) {
    if current_path.contains(&node) {
        // Stop the chain, infinite loop.
        return;
    }

    let (curr_cond, next_conds) = conditions
        .split_first()
        .expect("condition list must not be empty");

    if !next_conds.is_empty() && !curr_cond.must_match_again(condition_match_count) {
        // Try the next condition for the current node if there are more
        // and the current condition is already fulfilled.
        find_matches_recursively(graph, node, next_conds, current_path, matching_paths, 0);
    }

    if (curr_cond.matches)(&graph.nodes[node]) {
        let mut path = current_path.to_vec();
        path.push(node);
        let match_count = condition_match_count + 1;

        if !next_conds.is_empty() {
            // If there are more conditions, try the next one for all children.
            for &child in &graph.nodes[node].children {
                find_matches_recursively(graph, child, next_conds, &path, matching_paths, 0);
            }
        }
        if curr_cond.can_match_again(match_count) {
            // If we can match the current condition again, try for all children.
            for &child in &graph.nodes[node].children {
                find_matches_recursively(graph, child, conditions, &path, matching_paths, match_count);
            }
        }
        if next_conds.is_empty() {
            // Matched a full unique search pattern.
            matching_paths.insert(path);
        }
    }
}
