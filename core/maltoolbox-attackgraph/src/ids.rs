use slotmap::new_key_type;

new_key_type! {
    /// Generational key for an [`crate::node::AttackGraphNode`].
    ///
    /// Distinct from `AttackGraphNode::id` (the stable, user/file-facing
    /// `i64`): `partially_regenerate_graph` adds and removes nodes at
    /// runtime, and a generational key lets a handle held across such a
    /// mutation detect "gone" instead of silently aliasing a reused slot.
    pub struct AttackGraphNodeId;
}
