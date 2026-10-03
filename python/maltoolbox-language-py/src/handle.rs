//! Shared helper for the owner+id "handle" pattern used by
//! `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep`, with `__hash__`/
//! `__richcmp__` keyed on `(owner pointer identity, id)` rather than
//! CPython's default object-identity hash/eq, so two separately-built
//! handles for the same logical item compare equal and hash the same
//! (required for `dict`/`set` keying - see
//! PYTHON_BINDINGS_IMPLEMENTATION.md's "Container / handle pattern").
//!
//! **Per-owner handle cache (Phase 4 decision 1).** Originally these
//! handles were *also* never cached - a fresh Rust value (and therefore
//! a fresh Python object) was built on every access, relying solely on
//! `composite_hash`/structural `__richcmp__` for `dict`/`set` keying.
//! Phase 4 found this incomplete: `tests/attackgraph/
//! test_attackgraph.py::test_attackgraph_deepcopy` asserts `id(same_node)
//! == id(node)` across two *separate* attribute accesses - real Python
//! object identity, not just `==` - and the user confirmed mal-simulator
//! relies on this too. `HandleCache`/`new_handle_cache`/`cached_handle`
//! below implement a per-owner cache (one `HashMap<id, Py<Handle>>` per
//! container instance) so repeated lookups for the same id within the
//! same owner return the identical Python object, while two different
//! owner instances (even structurally identical ones) never share
//! identity, since each owns a separate cache. This is additive to, not
//! a replacement for, `composite_hash`/`__richcmp__`: those still matter
//! on a cache miss (a freshly-built handle comparing against something
//! already in a `set`/`dict`) and for cross-owner comparisons (which the
//! cache deliberately doesn't unify).

use std::cell::RefCell;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::PyClass;

use maltoolbox_language::graph::ids::{AssetId, AttackStepId};

use crate::asset::PyLanguageGraphAsset;
use crate::attack_step::PyLanguageGraphAttackStep;

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

/// Per-owner cache of previously-built handles, keyed by stable id.
pub type HandleCache<K, V> = Rc<RefCell<HashMap<K, Py<V>>>>;

pub fn new_handle_cache<K, V>() -> HandleCache<K, V> {
    Rc::new(RefCell::new(HashMap::new()))
}

/// Looks up `key` in `cache`. On a hit, returns the same `Py<V>` (via
/// `clone_ref` - bumping the refcount, not constructing a new Python
/// object). On a miss, builds a fresh `V` via `build`, wraps it in a new
/// `Py<V>`, inserts it into the cache, and returns it - `build` only
/// runs on a miss, so it's fine for it to do real work (clone an `Rc`,
/// etc.).
pub fn cached_handle<K, V>(cache: &HandleCache<K, V>, py: Python<'_>, key: K, build: impl FnOnce() -> V) -> PyResult<Py<V>>
where
    K: Eq + Hash,
    V: PyClass + Into<PyClassInitializer<V>>,
{
    if let Some(existing) = cache.borrow().get(&key) {
        return Ok(existing.clone_ref(py));
    }
    let py_obj = Py::new(py, build())?;
    cache.borrow_mut().insert(key, py_obj.clone_ref(py));
    Ok(py_obj)
}

/// Bundles every handle-type cache a `LanguageGraph` needs into one
/// `Rc`, so `PyLanguageGraph`/`PyLanguageGraphAsset`/
/// `PyLanguageGraphAttackStep` (and cross-crate consumers like
/// `PyModelAsset`/`PyAttackGraphNode`, which each need to build a
/// `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep` of their own) can
/// all share the *same* two caches via a single extra field and one
/// cheap `Rc` clone, rather than threading two separate cache fields
/// everywhere.
pub struct LangGraphCaches {
    pub assets: HandleCache<AssetId, PyLanguageGraphAsset>,
    pub steps: HandleCache<AttackStepId, PyLanguageGraphAttackStep>,
}

impl LangGraphCaches {
    pub fn new() -> Rc<Self> {
        Rc::new(LangGraphCaches {
            assets: new_handle_cache(),
            steps: new_handle_cache(),
        })
    }
}

pub type SharedLangGraphCaches = Rc<LangGraphCaches>;
