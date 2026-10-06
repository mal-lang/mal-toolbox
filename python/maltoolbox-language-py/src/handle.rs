//! Shared helper for the owner+id "handle" pattern used by
//! `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep`: each handle borrows
//! its owner transiently and looks itself up by id rather than holding a
//! copy. `__hash__`/`__richcmp__` are keyed on `(owner pointer identity,
//! id)` rather than CPython's default object-identity hash/eq, so two
//! separately-built handles for the same logical item compare equal and
//! hash the same, which `dict`/`set` keying requires.
//!
//! On top of that, `HandleCache`/`new_handle_cache`/`cached_handle` add a
//! per-owner cache (one `HashMap<id, Py<Handle>>` per container instance)
//! so repeated lookups for the same id on the same owner return the
//! identical Python object (`id(a) == id(b)`), which Python code that
//! relies on object identity (not just `==`) needs. Two different owner
//! instances never share identity, even if structurally identical, since
//! each owns a separate cache. This is additive to `composite_hash`/
//! `__richcmp__`, not a replacement: those still matter on a cache miss
//! and for cross-owner comparisons, which the cache deliberately doesn't
//! unify.

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
/// for returning directly from `__hash__`. Truncating the `u64` to
/// `isize` is fine: Python only requires equal objects to hash equally
/// within a process, not within a specific range.
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

/// Looks up `key` in `cache`. On a hit, returns the same `Py<V>` via
/// `clone_ref` (bumps the refcount, doesn't construct a new Python
/// object). On a miss, builds a fresh `V` via `build`, wraps it in a new
/// `Py<V>`, inserts it into the cache, and returns it.
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
/// `Rc`, so `PyLanguageGraph`, its handles, and cross-crate consumers
/// (e.g. `PyModelAsset`, `PyAttackGraphNode`) can all share the same
/// caches via one field and a cheap `Rc` clone.
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
