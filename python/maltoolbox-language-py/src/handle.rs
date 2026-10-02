//! Shared helper for the owner+id "handle" pattern used by
//! `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep`: constructed fresh
//! on every access (never cached - see
//! PYTHON_BINDINGS_IMPLEMENTATION.md's "Container / handle pattern"),
//! with `__hash__`/`__richcmp__` keyed on `(owner pointer identity, id)`
//! rather than CPython's default object-identity hash/eq, so two
//! separately-constructed handles for the same logical item compare
//! equal and hash the same (required for `dict`/`set` keying - see the
//! same section for why).

use std::hash::{Hash, Hasher};

/// Computes a stable `isize` hash for a `(owner ptr, id)` pair, suitable
/// for returning directly from `__hash__`. Wrapping the `u64` down to
/// `isize` is fine: Python only requires equal objects hash equally
/// within a single process, not a specific range.
pub fn composite_hash<T: Hash>(owner_ptr: usize, id: T) -> isize {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    owner_ptr.hash(&mut hasher);
    id.hash(&mut hasher);
    hasher.finish() as isize
}
