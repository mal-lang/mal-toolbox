use slotmap::new_key_type;

new_key_type! {
    /// Generational key for an [`crate::node::AttackGraphNode`].
    ///
    /// Distinct from `AttackGraphNode::id` (the stable, user/file-facing
    /// `i64`): partial regeneration (`partially_regenerate_graph`) adds
    /// and removes nodes at runtime, so a handle held across such a
    /// mutation needs to safely report "gone" instead of silently
    /// aliasing a reused slot - which is exactly what a generational key
    /// (and a plain integer index) would not do.
    pub struct AttackGraphNodeId;
}
