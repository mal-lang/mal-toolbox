# Python bindings implementation plan & status

This document is the working plan *and* the live status tracker for
replacing `mal-toolbox`'s pure-Python implementation with one backed
entirely by the Rust core (`crates/`), via a new PyO3 compatibility
layer. It is written to be re-entrant: read "Status" first to see where
things stand, then the rest for the reasoning behind decisions already
made. Update "Status" (and any plan section it invalidates) at the end
of every work session, before context is compacted.

## Goal

`maltoolbox`'s public Python API (class names, method signatures,
attributes, exceptions, pickling, dict shapes) stays **exactly** as it
is today. Underneath, every one of those classes becomes a thin wrapper
around the Rust core. There is no dual-backend runtime switch and no
pure-Python fallback path left behind - once a layer is done, its
pure-Python module is replaced. The pure-Rust core crates
(`maltoolbox-language`, `maltoolbox-model`, `maltoolbox-attackgraph`,
`maltoolbox-fileutil`, `maltoolbox-patternfinder`, `maltoolbox-cli`)
remain usable standalone by non-Python consumers with no Python
dependency at all - the compat crates are an additional, separate thing
layered on top, not a replacement for the core crates' own API.

**Acceptance gate:** [mal-simulator](https://github.com/mal-lang/mal-simulator)'s
`main` branch, completely unmodified, must keep passing its own test
suite when installed against a Rust-backed `mal-toolbox`. This is the
real-world compatibility signal - not a test we wrote ourselves. See
"Findings from mal-simulator" below for what this already told us about
the required surface.

## Non-goals / explicitly out of scope

- A dual pure-Python/Rust runtime switch. (Earlier drafts of this plan
  had one; dropped - see conversation history. Rust is the only
  backend.)
- Changing anything about the five existing core crates' public APIs.
  The compat crates are additive consumers of already-public items.
- Changing the root `Cargo.toml` workspace `members` list. The compat
  crates live under `python/` and are deliberately **not** members of
  the root workspace (each has its own empty `[workspace]` table) so
  that `cargo build --workspace`/`cargo test --workspace`/CI never pick
  them up and never need libpython headers. Verified: both commands
  still report the same totals (117 tests) after adding `python/`.

## Architecture

### Crate layout

One compat crate per existing core layer, mirroring the
`maltoolbox-language`/`maltoolbox-model`/`maltoolbox-attackgraph` split,
plus one umbrella crate that is the actual `maturin` build target:

```
python/
  maltoolbox-language-py/   - PyLanguageGraph (+ its exceptions)
  maltoolbox-model-py/      - PyModel, PyModelAsset               (not started)
  maltoolbox-attackgraph-py/- PyAttackGraph, PyAttackGraphNode     (not started)
  maltoolbox-pyo3/          - umbrella: assembles the above into
                              `maltoolbox._native`, the only crate
                              with pyo3's `extension-module` feature
                              and the only one with a pyproject.toml
```

Each layer crate is a plain `rlib` depending on `pyo3` with **default
features** (no `extension-module`) - only the umbrella enables
`extension-module`. This is the standard multi-crate PyO3 pattern:
enabling `extension-module` on a non-final crate breaks linking
(undefined libpython symbols) and breaks that crate's own `cargo test`.

Each layer crate exposes a `pub fn register(py: Python<'_>, m: &Bound<'_,
PyModule>) -> PyResult<()>` that the umbrella's `#[pymodule]` calls, one
per layer.

### Container / handle pattern (decided during planning, before any code)

- The three "container" types a Python user constructs directly -
  `LanguageGraph`, `Model`, `AttackGraph` - wrap `Rc<RefCell<T>>`
  around the real Rust struct from the core crate.
- `#[pyclass(unsendable)]` is required on all of them: they hold
  `Rc<RefCell<_>>`, not `Arc<Mutex<_>>`, and pyo3 (since the
  free-threading-readiness work landed) requires `Send + Sync` on
  pyclasses by default. `unsendable` is the correct, idiomatic opt-out
  here - the GIL already serializes all access from Python, so this
  only matters if some future free-threaded-Python build moved an
  instance across threads, which nothing here does. Confirmed necessary
  by an actual compiler error during Phase 0 (see Status).
- "Child" objects (`ModelAsset`, `AttackGraphNode`) are **handles**,
  not copies and not cached: `PyModelAsset { owner: Rc<RefCell<Model>>,
  id: i64 }`, `PyAttackGraphNode { owner: Rc<RefCell<AttackGraph>>, id:
  AttackGraphNodeId }`. Every method borrows `owner` transiently and
  looks the item up by id. Constructing a fresh handle is just an `Rc`
  clone - cheap, so **no handle cache is needed for mutation
  visibility** (two handles for the same id already see each other's
  mutations, since they deref the same `RefCell`).
- What a handle cache *would* have bought - and the cheaper fix we're
  using instead - is `dict`/`set` keying. CPython's default `__eq__`/
  `__hash__` for a type with neither overridden is identity-based, so
  two freshly-built handles for the same logical node would otherwise
  compare unequal. Confirmed via mal-simulator that this matters
  (`dict[AttackGraphNode, float]`). Fix: implement `__richcmp__`/
  `__hash__` on `PyModelAsset`/`PyAttackGraphNode` keyed on `(owner
  pointer identity via Rc::as_ptr, stable id)`, not on Python object
  identity. No cache required.
  - Known, accepted gap: `node_a is node_b` for two separately-obtained
    handles to the same logical node is `False` here, vs. always `True`
    in pure Python (one live object graph there). Checked: neither
    mal-toolbox's own test suite nor mal-simulator's `main` branch do
    any `is`-based identity comparison on these objects (grepped both,
    only found unrelated `is None`/`is not None`/`isinstance`). Safe to
    accept.
- `AttackGraph.model` (the compat `PyAttackGraph`) **does** store a
  real `Option<Py<PyModel>>` back-reference, even though the Rust core
  deliberately does not (see `PORTING_NOTES.md` §2). Confirmed
  necessary: mal-simulator calls `attack_graph.model` directly 29
  times. This lives only in the compat layer.
- Opaque id wrappers for slotmap keys (`AssetId`/`AttackStepId` from
  `maltoolbox-language`, `AttackGraphNodeId` from
  `maltoolbox-attackgraph`) are only needed where Python code needs to
  hold/compare/pass one back - e.g. `AttackGraphNode.lg_attack_step`.
  Not needed for `Model`/`ModelAsset`, since `Model` already keys
  assets by a stable, Python-native `i64`.

### Error -> exception mapping

Mirrors `maltoolbox/exceptions.py`'s hierarchy exactly, built with
`pyo3::create_exception!` once per layer and assembled onto the single
`_native` module namespace (all layers register into the same flat
`_native` module, so `MalToolboxException` itself is only defined once
- by the first layer to need it; see Status/Phase 2 for how later
layers reuse it rather than redefining).

```
MalToolboxException
├── LanguageGraphException
│   ├── LanguageGraphSuperAssetNotFoundError
│   ├── LanguageGraphAssociationError
│   └── LanguageGraphStepExpressionError
├── AttackGraphException
│   └── AttackGraphStepExpressionError
└── ModelException
    ├── ModelAssociationException
    └── DuplicateModelAssociationError
```

Known gap (tracked, not yet resolved): the Rust core's `LoadError`
(compiler/file errors) doesn't yet have a 1:1 mapping to a Python
exception type - the Python MAL compiler's own exception types were
never ported to this layer. Collapsed to the base
`LanguageGraphException` for now. Low risk (mal-simulator doesn't call
the compiler path - it only ever loads already-compiled `.mar`/
pre-built models), but worth closing before calling the language layer
fully done.

### `to_dict`/`from_dict` bridging

Via the `pythonize` crate (`serde_json::Value <-> PyObject`), since
every core type already funnels through `serde_json::Value`. No
hand-rolled converter.

### Pickling (required, not optional)

Confirmed via a real clone-and-grep of mal-simulator's `main` branch
(not assumed): `MALSimulatorStaticData` (a `NamedTuple` in
`malsim/mal_simulator/simulator_static_data.py`) holds a live
`AttackGraph` object directly, and
`tests/test_mal_simulator.py::test_simulator_picklable` pickles the
whole simulator and asserts
`restored.sim_state.attack_graph._to_dict() == ...` after an
unpickle round-trip. `PORTING_NOTES.md` §1 excluding pickle *tests*
from the pure-Rust port doesn't carry over here - a real downstream
consumer pickles these objects, so the compat layer must support it.

Plan (not yet implemented): `__getstate__`/`__setstate__` on each
compat class, implemented in terms of the already-correct
`to_dict`/`from_dict`, bundling whatever's needed to reconstruct
`lang_graph` standalone (likely the compiled langspec JSON, so a
restored object doesn't need the original `.mal`/`.mar` file on disk).
Needs its own conformance test mirroring
`test_simulator_picklable` before trusting it.

### Findings from mal-simulator (ground truth, not assumption)

Obtained by `gh repo clone --depth 1 mal-lang/mal-simulator` into
`/tmp` (deleted after inspection, not committed anywhere) and
grepping. Confirmed concrete, real usage of the surface this layer
must replicate:

```
57  attack_graph.add_node
51  attack_graph.get_node_by_full_name
48  model.get_asset_by_name
38  model.assets
38  attack_graph.nodes
29  model.add_asset
29  attack_graph.model
 9  model.lang_graph
 3  model.remove_asset
 3  attack_graph._to_dict        <- underscore-prefixed "private" method, called directly
 3  attack_graph.partially_regenerate_graph
 3  attack_graph.detectors
 3  attack_graph.attack_steps
 2  model.to_dict
 2  model.next_id
 2  lang_graph.assets
 1  lang_graph.metadata
 1  attack_graph.save_to_file
 1  attack_graph.lang_graph
 1  attack_graph.defense_steps
```

Takeaway: the de facto compatibility surface is wider than the
documented public API - underscore-prefixed methods like `_to_dict`
are relied on directly and must be replicated exactly, not just the
nominally-public ones.

Also confirmed no class in either `mal-toolbox`'s own tests or
mal-simulator's `main` overrides `__eq__`/`__hash__`, and neither does
any `is`-based identity comparison on these objects - both facts used
above to justify skipping a handle cache.

### Packaging (Phase 5, not started)

This is a deliberate, acknowledged break to the **build/release**
pipeline - never to the Python API surface:

- `pyproject.toml`'s `[build-system]` moves from `setuptools` to
  `maturin`.
- `mal-toolbox` becomes a compiled-extension package unconditionally
  (same category as `pydantic`/`polars`/`ruff`). Prebuilt wheels for
  common platforms via `maturin`+`cibuildwheel` become necessary;
  building from sdist on an uncovered platform now requires a Rust
  toolchain, where today it never did.
- Still TODO even for local dev (see Status): get `maturin`'s
  `module-name = "maltoolbox._native"` to install the compiled
  extension *inside* the existing `maltoolbox/` source directory
  automatically. Phase 0 found that without a `python-source` pointing
  at a directory that actually contains a `maltoolbox/` package,
  maturin installs a bare top-level `_native` package instead (wrong
  location) - worked around for now by manually copying the built
  `.so` into `maltoolbox/` (gitignored, not committed, not a real fix).
  Proper fix is Phase 5's job: likely `python-source = "../.."` (repo
  root) once `maltoolbox/*.py` are themselves just re-export shims, so
  maturin owning the whole source tree during `maturin develop` doesn't
  fight with anything else.

## Phasing

- [x] **Phase 0 - scaffolding & pipeline proof.** `python/` directory,
  `maltoolbox-language-py` + `maltoolbox-pyo3` crates, exception
  hierarchy skeleton (`MalToolboxException`/`LanguageGraphException` +
  3 subtypes), a real (if minimal) `PyLanguageGraph` wrapping
  `load_from_file`/`from_mal_spec`/`from_mar_archive`/`save_to_file`/
  `to_dict`/`metadata`/`__repr__`. Verified end-to-end against a real
  `.mar` fixture: loads, `to_dict()` matches the expected asset-keyed
  shape, error path raises `LanguageGraphException` which `issubclass`s
  `MalToolboxException`. `cargo build --workspace`/`cargo test
  --workspace` confirmed unaffected (same 117 tests as before `python/`
  existed). **Done.**
- [x] **Phase 1 - `LanguageGraph` full parity.** Flesh out
  `maltoolbox-language-py` to full method/attribute parity with
  `maltoolbox/language/languagegraph.py`: dict-like `.assets` (keyed by
  *name*, matching Python - confirmed via source read, not the current
  placeholder `asset_names()` list), per-asset/attack-step accessors
  (`LanguageGraphAsset`, `LanguageGraphAttackStep` wrappers - note:
  these weren't in the original 5-type request, but `.assets`/
  `lang_graph.assets` being real objects elsewhere (not just dicts) in
  the Python original means they likely need their own thin wrapper
  too; confirm against `language_graph_asset.py`/
  `language_graph_attack_step.py` before assuming), proper exception
  mapping for `LoadError`/compiler errors (currently collapsed to the
  base exception - see gap above), pickling. Conformance tests: run
  against the same fixtures already used by `crates/maltoolbox-
  language`'s own tests, diff `to_dict()` output.
- [x] **Phase 2 - `Model`/`ModelAsset`.** New `maltoolbox-model-py`
  crate. `PyModel(Rc<RefCell<Model>>)`, `PyModelAsset` handle (owner +
  `i64` id, no cache). `__richcmp__`/`__hash__` by `(owner ptr, id)`.
  `ModelException` family. Post-removal readability (the one gap that
  blocked completion) resolved via the `AssetSnapshot` tombstone
  mechanism - see Status.
- [ ] **Phase 3 - `AttackGraph`/`AttackGraphNode`.** New
  `maltoolbox-attackgraph-py` crate. `PyAttackGraph(Rc<RefCell<
  AttackGraph>>)` **plus** the `Option<Py<PyModel>>` back-reference for
  `.model`. `PyAttackGraphNode` handle (owner + `AttackGraphNodeId`, no
  cache), `__richcmp__`/`__hash__` by `(owner ptr, id)`. This is where
  the pickling design actually gets implemented and tested (`AttackGraph`
  is what mal-simulator pickles). `AttackGraphException` family.
- [ ] **Phase 4 - cut over.** Replace `maltoolbox/{model,language/
  languagegraph,attackgraph/{attackgraph,node}}.py` with thin
  re-export shims pointing at `maltoolbox._native`. Keep shims (not an
  immediate hard delete) until Phase 6's gate passes, then delete the
  superseded pure-Python logic outright.
- [ ] **Phase 5 - packaging.** `maturin` build backend, `python-source`
  wiring so the extension lands inside `maltoolbox/` properly (see
  "Packaging" above), `cibuildwheel` CI config, sdist-requires-Rust
  documented in README.
- [ ] **Phase 6 - mal-simulator acceptance gate.** Clone mal-simulator
  `main` unmodified, install this repo's Rust-backed wheel as its
  `mal-toolbox` dependency, run its test suite unmodified. Must pass.

## Phase 1 decisions (settled before implementation started)

Asked the user explicitly rather than assuming; answers below are
binding for Phase 1 and the default going forward unless a later phase
gives a concrete reason to deviate (note the reason if so).

1. **`.assets`/`.attack_steps`/`.associations` exposure:** a plain
   Python `dict` rebuilt fresh on every property access (values are
   still live owner+id handles, not snapshots - correctness is
   unaffected by rebuilding the dict itself). Not a custom lazy Mapping
   pyclass - rejected as unneeded complexity for graphs this size
   (coreLang has 19 top-level assets) and because `LanguageGraph` never
   mutates after construction, so there's no staleness risk to design
   around.
2. **`LanguageGraphAsset`/`LanguageGraphAttackStep` get full
   handle-based wrapper classes in Phase 1**, not deferred. Confirmed
   necessary by grep, not assumed: `tests/test_model.py:100` does
   `ModelAsset(..., lg_asset=lang_graph.assets['Application'])`,
   `tests/attackgraph/test_partial_regeneration.py` and
   `tests/patternfinder/test_attackgraph_patterns.py` do the same
   pattern with attack steps/associations threaded into
   `AttackGraphNode(...)` constructors directly. These are a hard
   prerequisite for `ModelAsset.lg_asset`/`AttackGraphNode
   .lg_attack_step` in Phases 2-3 regardless, so building them now
   avoids redoing this work.
3. **Full compiler-error exception mapping, built now** (not deferred,
   despite mal-simulator never exercising the compile path). Mirrors
   two *separate* existing Python hierarchies - neither is under
   `MalToolboxException`:
   - `maltoolbox.language.compiler.exceptions.MalCompilerError`
     (`Exception` subclass) with children `MalSyntaxError` (carries
     `.line`/`.column`), `MalParseError`, `MalTypeError`,
     `MalNameError`, `MalCompilationError`.
   - `maltoolbox.language.compiler.mal_analyzer.malAnalyzerException`
     (separate `Exception` subclass, unrelated hierarchy - note the
     unconventional lowercase-`m` class name, which must be preserved
     exactly: `assoc_traversal_processor.py` imports and raises it by
     that exact name).
   Confirmed load-bearing, not just nominal: `tests/language/
   test_detectors.py` does `from maltoolbox.language.compiler.exceptions
   import MalCompilerError` and `pytest.raises(MalCompilerError)`
   directly - this is one of the existing tests the cutover (Phase 4)
   must keep passing.
   Rust `CompileError` -> Python mapping (the Rust port's compiler
   doesn't distinguish `Semantic` from a general parse/type/name error
   as finely as Python's hierarchy does, so this is a many-to-fewer
   mapping, documented so the gap is visible rather than silent):
   - `CompileError::Syntax{path,line,column}` -> `MalSyntaxError(msg,
     line=line, column=column)`
   - `CompileError::Malformed(_)` -> `MalCompilerError` (base; Rust
     doesn't currently distinguish parse/type/name sub-cases)
   - `CompileError::Semantic(_)` -> `malAnalyzerException` (the
     *other* hierarchy - matches Python, where semantic-analysis
     errors come from `mal_analyzer.py`, not `mal_compiler.py`)
   - `CompileError::Io{..}` -> a plain Python `OSError` (not a custom
     type) - matches Python, which lets a raw file-read failure
     propagate unwrapped rather than catching and rewrapping it.
4. **Core-crate changes: opportunistic only, flagged individually as
   made.** No core changes identified as necessary for Phase 1 itself -
   everything needed (`asset_id_by_name`, `LanguageGraphAsset
   .attack_steps: HashMap<String, AttackStepId>`, `.own_associations:
   HashMap<String, Rc<LanguageGraphAssociation>>`) is already public
   and name-keyed.

## Significant finding from Phase 1: freeform/mutable construction is load-bearing test infrastructure

Not resolved - flagged here for a decision before Phase 1 can be called
fully done, and before Phase 2/3 repeat the same shape of problem with
`Model`/`AttackGraph`.

`tests/conftest.py`'s `dummy_lang_graph` fixture (used by multiple test
files, e.g. `tests/patternfinder/test_attackgraph_patterns.py`,
referenced indirectly by others) does this:

```python
lang_graph = LanguageGraph()                                   # no lang_spec at all
dummy_asset = LanguageGraphAsset(name='DummyAsset')             # bare dataclass, no graph involved
lang_graph.assets['DummyAsset'] = dummy_asset                   # plain dict item-assignment
dummy_or_attack_step_node = LanguageGraphAttackStep(
    name='DummyOrAttackStep', type='or', asset=dummy_asset
)
dummy_asset.attack_steps['DummyOrAttackStep'] = dummy_or_attack_step_node
```

This is **not reconcilable with the owner+id handle design as built**.
`PyLanguageGraphAsset`/`PyLanguageGraphAttackStep` are handles into a
specific `LanguageGraph`'s `SlotMap`-backed arena - `AttackStepId`
*is* a key into that one graph's `steps: SlotMap<AttackStepId, _>`.
Python's dataclasses need no such backing: a bare `LanguageGraphAsset(
name=...)` is fully self-contained state, freely constructible,
re-parentable, and assignable into any `LanguageGraph.assets` dict after
the fact - there is no equivalent "detached, self-contained" construction
path in this binding layer, nor in the arena-based core crate it wraps.

This was **not attempted** in this pass - it's a real architecture fork,
not a bug to quietly patch around under time pressure. Options, for the
coordinator/user to pick from:

1. **Retire/rewrite the affected fixtures** to compile a tiny real
   `.mal` spec string through the real pipeline instead of hand-building
   dataclass instances. Smallest implementation cost on the Rust side
   (zero - nothing changes here), but touches existing test files, and
   only covers tests that use `dummy_lang_graph`/equivalent patterns -
   need to grep exhaustively for how many that actually is before
   committing to this.
2. **Add a genuine freeform/mutable construction mode**: `LanguageGraph()`
   with no spec creates an empty, mutable graph (core-crate addition:
   `LanguageGraph::empty()`, small and easily justified, mirrors the
   existing `AttackGraph::empty(lang_graph)` pattern already in
   `maltoolbox-attackgraph`), and bare `LanguageGraphAsset(name=...)`/
   `LanguageGraphAttackStep(name=..., type=..., asset=...)` constructors
   implicitly insert themselves into *some* graph - but *which* graph,
   before `lang_graph.assets['DummyAsset'] = dummy_asset` has even run,
   is the unresolved design question. Meaningfully larger effort than
   anything else in Phase 1 so far.
3. **Accept these specific tests don't pass post-cutover**, documented
   as an explicit, known test-suite regression - contradicts "keep the
   existing `tests/` suite passing" as a Phase 1-3 implicit acceptance
   bar, so this would need to be a deliberate, explicit call, not a
   silent gap.

This doesn't block the compiled-graph-backed read path (the part that
matters for mal-simulator, which never does this) from being considered
solid - but it blocks calling Phase 1 *fully* done, and the identical
problem will resurface in Phase 2 (`Model`/`ModelAsset`) and Phase 3
(`AttackGraphNode`/`ExpressionsChain` - `tests/attackgraph/
test_partial_regeneration.py` constructs raw `ExpressionsChain(...)`
instances directly too, same pattern) unless resolved once, here, in a
way that generalizes.

**Decision (user, after reviewing all three options): rewrite the
fixtures (option 1).** Rationale given: zero Rust/binding-architecture
cost, and it only touches internal test infrastructure, not public API
or anything mal-simulator-relevant.

**Scope, confirmed by grep (`grep -rln "LanguageGraphAsset(\|
LanguageGraphAttackStep(\|ExpressionsChain(" tests/ maltoolbox/`) -
smaller and more contained than it first looked, but one consumer is
structurally bigger than a fixture swap:**
- `tests/conftest.py`'s `dummy_lang_graph` fixture (the only
  `LanguageGraphAsset`/`LanguageGraphAttackStep` hand-construction
  site) is used by exactly one test file:
  `tests/patternfinder/test_attackgraph_patterns.py`.
- That file's `test_attackgraph_find_multiple` turns out to go much
  further than consuming the fixture: it directly constructs
  `AttackGraph(dummy_lang_graph, Model(...))` and seven
  `AttackGraphNode(...)` instances, hand-assigns `.parents`/`.children`
  as raw Python `set`s, and replaces the whole graph's node storage
  outright (`attack_graph.nodes = {node1.id: node1, ...}`) - bypassing
  `AttackGraph`/`Model`/`AttackGraphNode` construction entirely, not
  just `LanguageGraph`. This can't be fixed by rewriting
  `dummy_lang_graph` alone; the test itself needs to build its tree
  topology through real APIs (`model.add_asset`, a real `AttackGraph`,
  and whatever the real public way to add/link nodes is - e.g.
  `attack_graph.add_node`/setting `.children`/`.parents` the supported
  way, not a raw dict swap) once a `LanguageGraph` with a `DummyAsset`
  (5 attack steps, one per `AttackStepType`) exists to build on.
- `tests/attackgraph/test_partial_regeneration.py`'s raw
  `ExpressionsChain(...)` construction (6 call sites) is a **separate,
  Phase 3 concern** - it's used to hand-build custom associations for
  partial-regeneration tests, not part of the `dummy_lang_graph`
  pattern, and doesn't block Phase 1. Left for Phase 3 as already
  noted above.

## Phase 2 decisions (settled before implementation started)

Asked the user before writing code, same as Phase 1's decisions. Binding
for Phase 2 and the default for Phase 3 unless a concrete reason to
deviate shows up there (note it if so).

1. **Shared `MalToolboxException` base: `maltoolbox-model-py` takes a
   direct crate dependency on `maltoolbox-language-py`** and reuses its
   already-exported `MalToolboxException` type for
   `create_exception!(_native, ModelException, MalToolboxException)`,
   rather than (a) extracting shared exceptions into a new crate
   (rejected: would require retroactively touching Phase 1's
   already-committed `exceptions.rs`) or (b) collapsing the per-layer
   crate split entirely (rejected: bigger structural reversal than
   warranted by one shared base type). This mirrors an existing
   precedent at the core-crate level - `maltoolbox-model` (core)
   already depends on `maltoolbox-language` (core) - so it's not a new
   kind of dependency direction, just extending the same relationship
   to the `-py` crates. Applies identically to Phase 3's
   `AttackGraphException` (`maltoolbox-attackgraph-py` depending on
   `maltoolbox-language-py` for the same reason).
2. **`tests/test_model.py::test_model_remove_nonexisting_asset`
   (constructs a detached `ModelAsset(name=, asset_id=, lg_asset=)`
   with no backing `Model` - confirmed the real `ModelAsset.__init__`
   takes no model/owner argument at all, same shape as Phase 1's gap
   #1) gets rewritten**, not given a special detached-construction
   path. Construct the "not in this model" asset via a second real
   `Model` instance instead (e.g. `other_model.add_asset(...)`, then
   assert `model.remove_asset()` on it raises `LookupError`) - tests
   the identical behavior through real construction. Confirmed by grep
   this is the only call site of this pattern for `ModelAsset`.
3. **`Model`/`ModelAsset` pickling is deferred to Phase 3**, built
   together with `AttackGraph`'s pickling design rather than now.
   Rationale: `AttackGraph` nests a `Model`, which nests a
   `LanguageGraph`, and the actual mal-simulator-driven pickling
   requirement was discovered at the `AttackGraph` layer (see
   "Pickling (required, not optional)" above) - designing the whole
   nested shape top-down once avoids redoing it. Matches Phase 1's own
   stated reasoning for deferring `LanguageGraph` pickling the same
   way.
4. **`Model.lang_graph` identity**: not asked as a question (judged a
   clear win, not a tradeoff) - `PyModel` stores the actual
   `Py<PyLanguageGraph>` object passed into its constructor, not a
   freshly-extracted `Rc<RefCell<LanguageGraph>>` re-wrapped on each
   `.lang_graph` access. This preserves `model.lang_graph is
   original_lang_graph_object` - `True`, matching Python exactly - for
   free, and is simpler than the alternative besides.

## Status

**Current phase: Phase 0, 1, and 2 all done. Next: Phase 3
(`AttackGraph`/`AttackGraphNode`).**

### Resolution of the freeform/mutable-construction finding (closes out Phase 1)

Implemented per the user's decision (option 1, rewrite the fixtures).
Turned out smaller than the three-option writeup worried it might be:

- Added `tests/testdata/dummy_lang.mal`: a minimal real MAL spec - one
  asset (`DummyAsset`) with one attack step of each type, using the
  exact names the old fixture used
  (`DummyOrAttackStep`/`DummyAndAttackStep`/`DummyDefenseAttackStep`/
  `DummyExistAttackStep`/`DummyNotExistAttackStep`), plus a reflexive
  `DummyAssoc` association so the `exist`/`notExist` steps have
  something to point their required `<-` clause at (MAL syntax doesn't
  allow a bare `exist`/`notExist` step with nothing to check existence
  of). Verified it compiles and produces exactly the 5 expected steps
  with correct types via a standalone check before touching any test
  file.
- Rewrote `tests/conftest.py`'s `dummy_lang_graph` fixture to one line:
  `LanguageGraph.from_mal_spec(path_testdata('dummy_lang.mal'))`.
  Dropped the now-unused `LanguageGraphAsset`/`LanguageGraphAttackStep`
  imports and the fixture's unused `corelang_lang_graph` parameter (the
  original fixture took it but never referenced it in the body either -
  not something this rewrite introduced).
- **`tests/patternfinder/test_attackgraph_patterns.py` needed zero
  changes**, contrary to the Phase 1 report's expectation that
  `test_attackgraph_find_multiple` would need rework. Investigated why:
  `AttackGraphNode.__init__` sets `self.children`/`self.parents` as
  plain `set()` attributes with no linking method, and
  `AttackGraph.__init__`/`_from_dict`'s own internals reassign
  `self.nodes` wholesale the same way the tests do
  (`self.nodes = {...}`/`.update(...)`) - so the tests' approach of
  direct attribute assignment was never the incompatible part; it's
  already the real, supported pattern in the pure-Python implementation.
  The *only* thing incompatible with the owner+id handle design was the
  detached `LanguageGraphAsset`/`LanguageGraphAttackStep` construction
  inside `dummy_lang_graph` itself. Once that fixture returns a real
  compiled graph, `.assets['DummyAsset']`/`.attack_steps[...]` just
  work and nothing downstream needed to change. (Two of the three
  consuming tests even construct `AttackGraph(None)` directly - also
  fine, confirmed by reading `AttackGraph.__init__`: `lang_graph` is
  just stored, only used if `model is not None`.)
- **Verified**: `uv run pytest tests/patternfinder/test_attackgraph_patterns.py -v`
  - all 4 tests pass unmodified. Full suite,
  `uv run pytest tests -m "not integration"` - **107 passed, 3
  deselected** (the 3 pre-existing `integration`-marked tests), same
  shape as before this change, confirming no other consumer depends on
  the old fixture's exact prior construction (re-grepped
  `dummy_lang_graph`/`LanguageGraphAsset(`/`LanguageGraphAttackStep(`
  across `tests/` post-change: only `tests/conftest.py` itself and
  `tests/attackgraph/test_partial_regeneration.py`'s already-out-of-scope
  `ExpressionsChain` usage remain). `ruff check` on both changed files:
  clean.
- **Confirmed against the Rust bindings too** (not just reasoned about):
  loaded `tests/testdata/dummy_lang.mal` through the already-built
  `_native.LanguageGraph.from_mal_spec` (no rebuild needed - Phase 1's
  `.so` was still current) and got the same 5 steps with correct types.
  So the rewritten fixture is provably compatible with both the
  pure-Python implementation (today) and the Rust bindings (post-Phase 4
  cutover).

Pickling (gap #5 below) remains intentionally deferred, not part of
what "done" means here - it was never blocking, just noted as a forward
dependency for Phase 3.

What exists on disk right now (`python/maltoolbox-language-py/src/`,
split into modules for readability - `lib.rs` just declares them and
calls each one's `register()`):
- `language_graph.rs` - `PyLanguageGraph`: `load_from_file`/
  `from_mal_spec`/`from_mar_archive` (all `#[staticmethod]`, simplified
  from Phase 0's unused-`cls` classmethods), `save_to_file`,
  `to_mar_archive`, `save_language_specification_to_json`,
  `regenerate_graph`, `metadata`/`lang_spec`/`assets` (dict, name-keyed)/
  `associations` (set)/`attack_steps` (set)/`fieldname_to_candidate_steps`
  getters, `_to_dict` (**renamed from Phase 0's `to_dict`** - the Python
  original only has `_to_dict`, no public `to_dict` method; Phase 0 had
  this wrong, caught and fixed while building Phase 1), `__repr__`.
- `asset.rs` - `PyLanguageGraphAsset`: owner+`AssetId` handle (not
  cached). `name`/`is_abstract`/`info`/`own_associations`/
  `attack_steps`/`own_super_asset`/`own_sub_assets`/`sub_assets`/
  `super_assets`/`associations`/`variables` getters,
  `associations_to`/`is_subasset_of`/`get_all_common_superassets`/
  `to_dict` methods, `__repr__`/`__hash__`/`__richcmp__` (eq/ne only,
  keyed on `(owner ptr, AssetId)` via the shared `handle::composite_hash`
  helper - not Python's default identity). All delegate to
  already-existing `LanguageGraph` methods in the core crate
  (`is_subasset_of`, `sub_assets`, `super_assets`, `associations`,
  `variables`, `associations_to`, `get_all_common_superassets`) - no
  core-crate changes needed here, confirming Phase 1 decision 4's
  prediction.
- `attack_step.rs` - `PyLanguageGraphAttackStep`: owner+`AttackStepId`
  handle. `name`/`type` (getter named via `#[getter(r#type)]` - `type`
  is a Rust keyword)/`asset`/`causal_mode`/`ttc`/`overrides`/`info`/
  `tags`/`inherits`/`own_children`/`own_parents`/`children` (own+
  inherited, via the core's existing `step.children(&graph)`)/
  `own_requires`/`requires`/`full_name` getters, `parents` getter
  **raises `NotImplementedError`** (matches the Python original exactly -
  it was never implemented there either, not a gap), `to_dict`,
  `__repr__`/`__hash__`/`__richcmp__` (same owner+id scheme).
  `own_children`/`own_parents`/`own_requires`/`requires` expose
  `ExpressionsChain` values via their serialized `to_dict()` form
  (pythonized), not a live wrapper object - see the gap noted below.
- `assoc.rs` - `PyLanguageGraphAssociation`/`PyLanguageGraphAssociationField`.
  Unlike the two above, these wrap the actual `Rc<LanguageGraphAssociation>`/
  a cloned `LanguageGraphAssociationField` value directly rather than an
  owner+id pair, since the core crate already has real structural
  `PartialEq`/`Hash` on `LanguageGraphAssociation` (excluding `info`,
  matching the Python dataclass's `compare=False`) - delegating to it is
  *more* faithful than an owner+id scheme would be, not just simpler
  (both sides of an association already share the same `Rc` in the core
  crate, matching Python's `left_asset.own_associations[...] = assoc;
  right_asset.own_associations[...] = assoc` - literally the same
  object on both sides). Full method parity: `name`/`left_field`/
  `right_field`/`info`/`full_name` getters, `get_field`/
  `contains_fieldname`/`contains_asset`/`get_opposite_fieldname`/
  `to_dict`, `__repr__`/`__hash__`/`__richcmp__`.
- `exceptions.rs` - full hierarchy per Phase 1 decision 3:
  `MalToolboxException`/`LanguageGraphException` branch (module string
  set to `maltoolbox.exceptions`, not this crate's own `_native` -
  see below for why this matters), plus the two separate compiler
  hierarchies: `MalCompilerError`/`MalSyntaxError` (carries `.line`/
  `.column` via a 3-tuple `new_err`)/`MalParseError`/`MalTypeError`/
  `MalNameError`/`MalCompilationError` (module string
  `maltoolbox.language.compiler.exceptions`), and
  `malAnalyzerException` (module string
  `maltoolbox.language.compiler.mal_analyzer`, exact lowercase-`m` name
  preserved via a `#[allow(non_camel_case_types)]`-wrapped submodule
  since `create_exception!` generates a real Rust type name that would
  otherwise trigger a lint). `graph_error_to_py`/`compile_error_to_py`/
  `load_error_to_py` implement the mapping table from Phase 1 decision
  3 exactly, including `CompileError::Io`/`LoadError::Archive`/
  `LoadError::FileUtil` -> plain `PyOSError` (confirmed correct by
  testing against a real `does/not/exist.mar` path - see Verification).
  **Why the module strings matter**: `create_exception!`'s first
  argument becomes the exception type's `__module__`, which `pickle`/
  `repr` use to *locate* the class. Setting it to the eventual Phase-4
  Python import path (not `_native`'s own internal nesting) now means a
  pickled exception instance will still resolve correctly after the
  Phase 4 shim swap, rather than silently breaking. Verified this
  actually works as intended (see Verification) - caught and fixed
  during this pass, wasn't in the original plan.
- `handle.rs` - shared `composite_hash(owner_ptr, id) -> isize` helper
  (`DefaultHasher` over `(ptr as usize, id)`), used by `asset.rs`/
  `attack_step.rs`'s `__hash__`.
- `lib.rs` - `register()` wires up all four classes + the exception
  hierarchy, and builds the nested submodule structure
  (`_native.language.compiler.exceptions`, `_native.language.compiler
  .mal_analyzer`) **with explicit `sys.modules` registration** for each
  level (`maltoolbox._native.language`, `...language.compiler`,
  `...language.compiler.exceptions`, `...language.compiler
  .mal_analyzer`) - without this, `from maltoolbox._native.language
  .compiler.exceptions import MalCompilerError`-style imports would fail
  even though attribute access (`_native.language.compiler.exceptions
  .MalCompilerError`) would work; pyo3 submodules aren't auto-registered
  in `sys.modules`. Verified both import styles work (see Verification).

Toolchain/pipeline (unchanged from Phase 0, still holds): `maturin
develop` (`VIRTUAL_ENV=.venv`) builds and installs cleanly; still
installs to the wrong location (bare top-level `_native` package, not
nested in `maltoolbox/`) since `python-source` isn't wired up yet
(Phase 5's job) - worked around the same way as Phase 0, by copying the
built `.so` into `maltoolbox/` (gitignored, not committed) and
uninstalling the stray top-level package. `cargo build --workspace`/
`cargo test --workspace` from repo root confirmed unaffected (same 117
tests, same pass/fail/ignored counts, as before Phase 1's changes).
`cargo clippy --all-targets` on both `python/` crates: zero warnings.

**Verification performed** (all against the real `org.mal-lang
.coreLang-1.0.0.mar` fixture already used throughout this project,
unless noted):
- **Oracle diff against the real pure-Python implementation** (the
  strongest check done this pass): loaded the same `.mar` file through
  both `_native.LanguageGraph.load_from_file` and the untouched
  `maltoolbox.language.languagegraph.LanguageGraph.from_mar_archive`
  (still fully intact pre-cutover) in the same process, called
  `._to_dict()` on both, JSON-round-tripped both (to normalize
  tuple/list representation noise) and compared: **exact match**. This
  covers the entire asset/attack-step/association/variable serialization
  surface in one shot, not just spot checks.
- Dict/set keying (the entire point of the owner+id `__hash__`/
  `__richcmp__` design): fetched the same asset via `g.assets['Application']`
  twice into two separate Python variables, confirmed `is` is `False`
  (separately constructed handles, as expected/accepted) but `==` is
  `True` and `{app, app2}` collapses to a 1-element set. Same check
  repeated for an attack step fetched two different ways
  (`app.attack_steps[name]` twice).
- Compiler exception mapping, against two minimal hand-written broken
  `.mal` snippets (scratch files under `/tmp`, not committed, deleted
  after use): an unclosed-brace syntax error raised
  `maltoolbox.language.compiler.exceptions.MalSyntaxError` (confirmed
  `issubclass` of `MalCompilerError`); `asset AA extends Nonexistent`
  raised `maltoolbox.language.compiler.mal_analyzer.malAnalyzerException`
  (confirmed *not* a subclass of `MalCompilerError` - separate
  hierarchy, as intended); a nonexistent `.mar` path raised a plain
  `OSError`, *not* under `MalToolboxException` (intentional, matches
  Python letting a raw file-read failure propagate unwrapped).
- `save_to_file` (`.json`/`.yml`)/`to_mar_archive`/
  `save_language_specification_to_json` all write successfully; reloading
  the `.json` and `.mar` outputs both reproduce the same asset count.
- `regenerate_graph`, `fieldname_to_candidate_steps` (66 fieldnames for
  coreLang), and the `parents` getter raising `NotImplementedError`
  (matching the Python original's own unimplemented stub, confirmed
  it's not a gap) all behave as expected.
- Nothing has been committed to git yet - `python/` and
  `PYTHON_BINDINGS_IMPLEMENTATION.md` are untracked (the user
  explicitly said not to commit).

**Open gaps, logged not silently skipped:**
1. ~~The freeform/mutable-construction architecture question above.~~
   **Resolved** - user chose option 1 (rewrite fixtures); done, see
   "Resolution of the freeform/mutable-construction finding" above.
   Still worth auditing `tests/conftest.py`'s `empty_model`/hand-built
   `ModelAsset` patterns for the identical shape of problem before
   assuming Phase 2 is a clean copy of this phase's approach.
2. `ExpressionsChain` has no wrapper class of its own yet - `own_children`/
   `own_parents`/`own_requires`/`requires`/`variables` all expose chain
   values via pythonized `to_dict()` dicts instead of a live object.
   Confirmed this doesn't affect serialization correctness (the full
   oracle diff above passed), but a caller that needs to *construct* or
   deeply inspect a chain object directly (as
   `tests/attackgraph/test_partial_regeneration.py` does, independently
   of `LanguageGraph` - itself an instance of gap #1's pattern) has no
   path to one here.
3. `LanguageGraphAttackStep.additive_model_effects`/
   `subtractive_model_effects`/`.detectors` properties are not exposed.
   No usage found anywhere in `tests/` or mal-simulator (grepped both),
   and the core crate's `LanguageGraphModelEffect` has no `to_dict`
   (confirmed by checking `model_effect.rs` - matches the Python
   original, which also excludes these from `to_dict()`'s output), so
   there's no cheap existing building block to wrap. Deferred, not
   forgotten.
4. The `LanguageGraph.process_*`/`reverse_expr_chain`/
   `_link_association_to_assets` methods (internal step-expression-
   processing plumbing used by the builder during compilation, not by
   anything post-construction) are not exposed. Grepped `tests/` for
   direct calls to any of these on a `LanguageGraph` instance: none
   found. Judged correctly out of scope rather than an oversight, since
   the Rust core's own builder already does this work internally during
   `generate_graph`/`compile_file` - exposing these would mean binding
   internal compiler mechanics nothing external calls.
5. No pickling support yet for `LanguageGraph`/`LanguageGraphAsset`/
   etc. Not required by mal-simulator directly for this layer (Phase 3's
   `AttackGraph` is what gets pickled there), but worth flagging now as
   a forward dependency: `AttackGraph`/`Model` both nest a
   `LanguageGraph`, so Phase 3's pickling work will need this layer
   picklable too, transitively. Not attempted this pass - scoping it
   belongs in Phase 3's design, not bolted on here speculatively.

**Next step:** Phase 1 is fully done. Start Phase 2 (`Model`/
`ModelAsset`) - audit `tests/conftest.py`'s `empty_model`/any hand-built
`ModelAsset` patterns early for the same freeform-construction shape of
problem gap #1 hit here, rather than discovering it mid-implementation
again.

### Phase 2 status: `Model`/`ModelAsset` (fully complete)

**Current phase: Phase 0, 1, and 2 all done. Next: Phase 3
(`AttackGraph`/`AttackGraphNode`).** The post-removal-readability gap
noted below is resolved - see "Resolution of the post-removal-
readability finding" further down.

New `python/maltoolbox-model-py` crate (depends on
`maltoolbox-language-py` per Phase 2 decision 1 - required `mod
exceptions`/`mod handle` in that crate to become `pub mod` so
`MalToolboxException`/`composite_hash` are reachable; zero behavioral
change, pure visibility):

- `exceptions.rs` - `ModelException(MalToolboxException)`,
  `ModelAssociationException`/`DuplicateModelAssociationError`
  (siblings under `ModelException` - defined for import-path parity
  only, confirmed by grep that neither is ever actually raised anywhere
  in the current codebase). `model_error_to_py` maps each `ModelError`
  variant to the *same plain built-in* Python would raise for the
  equivalent condition - confirmed line-by-line against
  `maltoolbox/model.py`'s real source, not assumed:
  `DuplicateAssetId`/`UnknownAssetType`/`DuplicateAssetName`/
  `TooManyAssetsInField`/`UnknownAssociation`/`Malformed` ->
  `ValueError`; `AssetNotFound`/`UnknownFieldname`/`UnknownAssetId` ->
  `LookupError`; `WrongAssociatedAssetType` -> `TypeError`;
  `NotAssociated` -> `KeyError`; `Language(GraphError)` delegates to
  `maltoolbox-language-py`'s `graph_error_to_py`. `UnknownAssetId`/
  `NotAssociated` have no exact Python precedent (the Rust core
  validates a couple of things Python doesn't check before a raw
  dict/set operation would fail) - approximated as the closest matching
  built-in, logged rather than silently picked. Separately,
  `load_error_to_py` *always* produces `ModelException` with Python's
  exact message ("Could not load model. It might be of an older
  version...") for the `load_from_file` entry point specifically,
  matching its real broad `except Exception as e: raise
  ModelException(...) from e` - confirmed this is the *only* place
  `ModelException` itself is actually raised in the real source.
  `from_dict_error_to_py` (unwrapped builtins) is used for the
  classmethod `_from_dict` path, which has no try/except in Python.
- `asset.rs` - `PyModelAsset`: owner (`Rc<RefCell<Model>>`) + `i64` id
  handle, **no `#[new]`** - confirmed nothing needs to construct a bare
  `ModelAsset` after the test rewrite (Phase 2 decision 2, see below).
  Full parity: `name`/`id`/`type` (via `#[getter(r#type)]`, `type` being
  a Rust keyword)/`lg_asset` (returns a `PyLanguageGraphAsset` handle -
  see the `lang_graph` field note below)/`defenses`/`extras`/
  `associated_assets` (dict-of-sets, rebuilt per access) getters,
  `associations_with`/`has_association_with`/
  `validate_associated_assets`/`add_associated_assets`/
  `remove_associated_assets`/`to_dict`/`_to_dict` methods,
  `__repr__`/`__hash__`/`__richcmp__` (owner-ptr+id scheme, reusing
  Phase 1's `handle::composite_hash`). `associated_assets`'s "needs
  id->name resolution via the owning Model" subtlety (noted in the core
  crate's own `ModelAsset::to_dict` doc comment) is handled the same
  way `Model::to_dict` handles it in Rust - filled in by `_to_dict`
  after calling the core method.
  - **Implementation wrinkle found while wiring up
    `add_associated_assets`/`remove_associated_assets`/
    `validate_associated_assets`**: these take `set[ModelAsset]` in
    Python, but pyo3's `Vec<PyRef<T>>` extraction only accepts
    `Sequence`s (list/tuple), not arbitrary iterables - a Python `set`
    argument raised `TypeError: 'set' object is not an instance of
    'Sequence'` at runtime (caught by testing, not by the compiler).
    Fixed with a small `ids_of(&Bound<PyAny>) -> HashSet<i64>` helper
    that calls `.try_iter()` instead, which accepts any iterable
    including sets.
- `model.rs` - `PyModel`: the one container type, holding **both**
  `inner: Rc<RefCell<maltoolbox_model::Model>>` (the core model) and
  `lang_graph_py: Py<PyLanguageGraph>` (the actual Python object passed
  to the constructor, per Phase 2 decision 4 - `.lang_graph` returns
  this directly via `clone_ref`, so `model.lang_graph is
  original_lang_graph_object` is confirmed `True`). `#[new]`/
  `load_from_file`/`_from_dict` all extract `Rc<RefCell<LanguageGraph>>`
  from `lang_graph_py` and **clone the `LanguageGraph` data once** to
  build the bare `Rc<LanguageGraph>` the core `Model` struct needs -
  see the new `#[derive(Clone)]` on the core `LanguageGraph` struct
  below for why this was necessary and what it costs. Full parity:
  `name` (getter+setter)/`lang_graph`/`maltoolbox_version`/`next_id`
  (getter+setter, confirmed via the earlier mal-simulator grep that
  `model.next_id` is accessed directly as a plain attribute)/`assets`
  (`dict[int, ModelAsset]`, id-keyed, rebuilt per access) getters,
  `add_asset`/`remove_asset`/`get_asset_by_id`/`get_asset_by_name`/
  `to_dict`/`_to_dict`/`save_to_file`/`load_from_file`
  (`#[staticmethod]`)/`_from_dict` (`#[staticmethod]`)/`__repr__`.
- **One opportunistic core-crate change, flagged per Phase 2 decision
  4**: added `#[derive(Clone)]` to `LanguageGraph` itself
  (`crates/maltoolbox-language/src/graph/mod.rs`) - needed because the
  core `maltoolbox_model::Model` requires a bare `Rc<LanguageGraph>`
  (no `RefCell`), which can't be produced from `PyLanguageGraph`'s
  `Rc<RefCell<LanguageGraph>>` without copying the data once (the two
  `Rc` flavors are different allocations; there's no safe zero-cost
  conversion between them). **Confirmed-narrow, accepted divergence**:
  a `Model` built this way holds its own independent copy of the
  language graph, so calling `regenerate_graph()` on the *original*
  `LanguageGraph` Python object afterward is not reflected in any
  `Model` already constructed from it. Grepped `tests/`/`maltoolbox/`
  for `regenerate_graph` usage: it's defined but never called anywhere
  outside its own definition - this divergence has no real-world
  trigger today, but is a real, confirmed semantic difference, not a
  purely cosmetic one. `cargo build --workspace`/`cargo test
  --workspace` confirmed unaffected by the derive (117 tests, same as
  before).
- Registered in `python/maltoolbox-pyo3` (`Cargo.toml` dependency +
  `maltoolbox_model_py::register(py, m)?` call), same pattern as Phase
  1.

**Phase 2 decision 2 implemented**: rewrote
`tests/test_model.py::test_model_remove_nonexisting_asset` to construct
the "not in this model" asset via a second real `Model` instance
(`other_model.add_asset(asset_type='Application', name='TestAsset')`)
instead of a detached `ModelAsset(...)` construction, then assert
`model.remove_asset()` on it still raises `LookupError`. Removed the
now-unused `ModelAsset` import from that file. Re-grepped
`tests/`/`maltoolbox/` for other `ModelAsset(` call sites after the
rewrite: only the real constructor definition itself
(`maltoolbox/model.py:102`, inside `add_asset`) and its own `__repr__`
format string remain - confirmed no other detached-construction site
exists for this type.

**Verified:**
- `cargo build`/`cargo clippy --all-targets` clean for
  `maltoolbox-model-py`, zero warnings (after fixing 6
  `doc_lazy_continuation` lints in a module doc comment - a markdown
  list-formatting nit, not a logic issue).
- `cargo build --workspace`/`cargo test --workspace`: still 117 tests,
  same as before Phase 2 (confirms `python/` crates remain correctly
  isolated from the root workspace even with the new crate + the
  `LanguageGraph: Clone` core change).
- `maturin develop` builds/installs cleanly (same known wrong-install-
  location workaround as Phase 0/1 - copy the built `.so` into
  `maltoolbox/`).
- **Oracle diff**: built an equivalent model (2 assets, one association)
  through both `_native.Model`/`ModelAsset` and the untouched
  `maltoolbox.model.Model`/`ModelAsset` in the same process, round-
  tripped both through `json.dumps`/`json.loads`, compared - **exact
  match**, after excluding the `"MAL-Toolbox Version"` metadata field
  (see the newly-confirmed oracle quirk below). Repeated after
  `remove_asset` - still an exact match.
  - **Newly confirmed Python oracle quirk** (found by running the real
    diff, not assumed): `Model.to_dict()` in the Python original always
    writes the live `maltoolbox.__version__` into `"MAL-Toolbox
    Version"`, **ignoring `self.maltoolbox_version` entirely** - the
    `mt_version` constructor argument (and whatever `_from_dict` reads
    back from a loaded file) is stored on `self.maltoolbox_version` but
    never read by `to_dict`. This is a distinct bug from the
    already-documented hyphenated-vs-spaced-key round-trip issue in
    `PORTING_NOTES.md` §3 (that one is about `_from_dict` reading the
    wrong key; this one is about `to_dict` ignoring the field that
    *is* correctly stored). This Rust port's `to_dict` correctly uses
    `self.maltoolbox_version` (matches the core crate's existing,
    already-written behavior - not a new choice made here), which is
    *more* useful but means an oracle diff must exclude this one field
    to compare meaningfully, exactly like `PORTING_NOTES.md` §3's other
    entries. Worth adding to `PORTING_NOTES.md` §3 at some point (not
    done here - out of scope for this binding-focused document, flagged
    for whoever next touches that file).
- Dict/set keying: fetched the same `ModelAsset` two different ways
  (`model.assets[id]` and `model.get_asset_by_name(name)`), confirmed
  `==`/`__hash__` match and `{a, b, c}` collapses to 1 element - same
  check Phase 1 did for language-graph handles.
  **Correctness bug caught and fixed by this check**: an earlier
  version of `PyModel::remove_asset` matched purely by `asset.id`
  without checking the asset's owner - meaning an asset handle from a
  *different* `Model` with a colliding `i64` id (e.g. both models'
  first-ever asset, both id `0`) would be silently accepted and the
  wrong asset removed. Investigated and determined Python's own
  `remove_asset` has the exact same purely-id-based check (confirmed
  by reading the source: `if asset.id not in self.assets`, no identity
  check) - so this isn't a divergence to fix, it's a faithful
  reproduction of a real (if arguably sloppy) Python behavior. Verified
  the actual rewritten test's conditions (a *fresh, empty* target
  model) don't hit this collision and correctly raise `LookupError`.
- Error mapping spot-checked against real conditions, not just read
  from the table: unknown asset type -> `ValueError`; unknown
  association fieldname -> `ValueError`; wrong-type association
  (`Application` <-> `Hardware` on `appExecutedApps`) -> `TypeError`;
  `load_from_file` on a nonexistent path -> `ModelException`
  (`issubclass` of `MalToolboxException` confirmed).
- `save_to_file`/`load_from_file` round-trip (`.yml`) reproduces an
  identical `to_dict()`.
- `uv run pytest tests/test_model.py -v`: 22/22 pass (pure-Python
  backend, includes the rewritten test). `uv run ruff check
  tests/test_model.py`: clean. Full suite: `uv run pytest tests -m "not
  integration"` - 107 passed, 3 deselected, identical to the baseline
  recorded after Phase 1's fixture rewrite - no regressions from either
  the core `Clone` derive or the test file edit.

**Open gap, logged not silently skipped - the thing standing between
"substantially complete" and "done":**

**Post-removal readability.** Confirmed by direct reproduction (not
theorized): a `PyModelAsset` handle resolves by looking up its `id` in
`owner.borrow().assets` on every access. Once `Model.remove_asset`
actually deletes that entry, the handle can no longer resolve *itself*
- any getter raises `LookupError`. But the real Python `ModelAsset` is
a plain, fully-independent object; removing it from `Model.assets` does
not destroy it, so reading its attributes afterward still works and
reflects whatever state it was left in during removal's cleanup (e.g.
its `associated_assets` getting emptied as a side effect of
`remove_asset` walking its associations before unlinking it).
`tests/test_model.py::test_model_remove_asset_with_association` reads
`asset1.associated_assets` *after* `model.remove_asset(asset1)` and
expects `{}` - reproduced directly against the native bindings:
constructing the identical scenario and reading the removed asset's
`.associated_assets` raises `LookupError` instead. Note this is
narrower than it might sound: a *surviving* asset whose associations
changed as a side effect of a *different* asset's removal reads back
correctly (verified) - only reading attributes of the asset that was
*itself* removed fails.

This is the `ModelAsset` analog of Phase 1's freeform-construction
finding, but **not the same fix** - decision 2's "rewrite the test"
approach doesn't apply here, since this isn't about detached
construction, it's about a handle outliving its backing data. The
likely real fix - identified but **not attempted this pass**, since
it's a core-crate restructuring, not a binding-layer one: change
`Model.assets` from `HashMap<i64, ModelAsset>` to `HashMap<i64,
Rc<RefCell<ModelAsset>>>`, so a `PyModelAsset` handle could hold the
`Rc<RefCell<ModelAsset>>` directly (cloned out before removal) instead
of an owner+id pair, giving it the same "stays readable, even
writable, after unlinking" behavior Python's object-reference model
gets for free. This would need `Model`'s every method
(`add_asset`/`remove_asset`/`get_asset_by_id`/`validate_associated_assets`/
`add_associated_assets`/`remove_associated_assets`/`to_dict`/...) to
switch to `.borrow()`/`.borrow_mut()` at each access site, and likely
touches `maltoolbox-attackgraph` too (it reads `Model.assets`/
`ModelAsset` fields directly when generating attack graph nodes) - a
blast radius well past "small, individually-justified" opportunistic
scope. Flagged for the coordinator/user to decide on, the same way
Phase 1's gap #1 was flagged rather than silently patched around.
`tests/test_model.py::test_model_remove_asset_with_association` is
**not rewritten** and **not currently passing against the native
bindings** (it still passes against the untouched pure-Python
implementation - nothing is cut over yet, so this doesn't fail any
test run today, but it is a landmine for Phase 4).

**Decision (user, after reviewing three options): extend
`RemovedAssetSnapshot` into a read-only tombstone**, not the
`Rc<RefCell<ModelAsset>>` restructuring the implementing fork proposed.
Rationale given: this codebase already has the identical pattern for
the identical problem - `RemovedAssetSnapshot` exists specifically so
`AttackGraph::partially_regenerate_graph` can answer "what was this
asset" after removal (`PORTING_NOTES.md` §2) - and the failing test only
*reads* a removed asset's attributes, never writes to it, so read-only
is sufficient and avoids the full `Model`-internals +
`maltoolbox-attackgraph` blast radius the other option would have had.

**Rename, per user follow-up**: now that this struct is growing beyond
"just what's needed after a removal" into a fuller snapshot of an
asset's state, rename it from `RemovedAssetSnapshot` to
**`AssetSnapshot`** everywhere (the struct definition and both call
sites - `Model::remove_asset` and `AttackGraph::partially_regenerate_graph`
in `maltoolbox-attackgraph`). Plain rename, no shape change beyond
decision described below.

Implementation shape (for whoever picks this up): `Model::remove_asset`
currently captures its `RemovedAssetSnapshot { name, lg_asset }` *before*
the associated-assets cleanup loop runs. Extend it (under its new name,
`AssetSnapshot`) to also capture the asset's full state
(defenses/extras/associated_assets/etc.) taken right before the final
`self.assets.remove(&asset_id)` line (i.e. *after* cleanup has already
mutated `associated_assets` in place) - this is a few-line change to one
function, not a restructuring, and the capture point already naturally
lands at the right moment since the existing code already reads the
live asset both before and after the cleanup loop. The compat layer's
`PyModel` keeps a `tombstones: HashMap<i64, ModelAsset>`-shaped record
populated from this on removal; `PyModelAsset`'s lookup falls back to it
when the live `owner.assets` lookup misses, giving read-only
post-removal access. Don't change the existing `name`/`lg_asset` fields
or their existing consumer in `maltoolbox-attackgraph` - only add to
the (renamed) struct and rename it at both call sites.

### Resolution of the post-removal-readability finding (closes out Phase 2)

Implemented exactly per the decision/rename above:

- `crates/maltoolbox-model/src/model.rs`: `RemovedAssetSnapshot` renamed
  to `AssetSnapshot`, with a new `final_state: ModelAsset` field.
  `Model::remove_asset` now captures `final_state` via a second
  `self.assets.get(&asset_id)` lookup placed right before
  `self.assets.remove(&asset_id)` - i.e. after the associated-assets
  cleanup loop has already run, so `final_state.associated_assets`
  reflects the post-cleanup (emptied) state. `name`/`lg_asset` fields
  and their capture point are unchanged.
- `crates/maltoolbox-attackgraph`: both the real consumer
  (`partially_generate.rs`/`graph.rs`) and the test helper in
  `tests/test_partial_regeneration.rs` (which constructs an
  `AssetSnapshot` directly from a still-live asset, for the
  call-partial-regeneration-before-remove_asset ordering) updated for
  the rename; the test helper also now fills in `final_state:
  asset.clone()`. Purely mechanical - no behavior change to the
  existing `name`/`lg_asset` consumer logic.
- `python/maltoolbox-model-py/src/model.rs`: `PyModel` gained a
  `tombstones: Tombstones` field (`Rc<RefCell<HashMap<i64,
  ModelAsset>>>`, type alias in `asset.rs`), initialized empty in
  `wrap`. `remove_asset` now captures the core's returned
  `AssetSnapshot` and inserts `snapshot.final_state` into `tombstones`
  keyed by the removed id, before returning.
- `python/maltoolbox-model-py/src/asset.rs`: `PyModelAsset` gained a
  `tombstones: Tombstones` field (threaded through `new` and both
  construction sites - `PyModel::asset_handle` and the sibling-handle
  construction inside the `associated_assets` getter). Added a
  `with_asset(&self, f: impl FnOnce(&ModelAsset) -> PyResult<R>) ->
  PyResult<R>` helper: tries the live `owner.assets` lookup first, falls
  back to `tombstones` on a miss, else raises `LookupError` - every
  read-only getter (`name`/`type`/`lg_asset`/`defenses`/`extras`/
  `associated_assets`/`__repr__`) now goes through it, so the fallback
  applies uniformly rather than per-method. `_to_dict` handles the two
  branches explicitly instead (it additionally needs the live `model`
  to resolve *other* assets' names for the id->name `associated_assets`
  mapping, which only applies in the live branch - a tombstoned asset's
  `associated_assets` is already empty, so there's nothing to resolve
  there). Mutating methods (`add_associated_assets`/
  `remove_associated_assets`/`validate_associated_assets`) were **not**
  changed - they still delegate straight to the core `Model` methods,
  which already reject an unknown/removed id on their own (confirmed:
  nothing requires mutating a removed asset, per the user's decision to
  keep this read-only).

**Verified:**
- `cargo build`/`cargo clippy --all-targets`: clean on
  `maltoolbox-model`, `maltoolbox-model-py`, `maltoolbox-attackgraph`,
  and the `maltoolbox-pyo3` umbrella - zero new warnings (the one
  pre-existing, unrelated `redundant_guards` warning in
  `maltoolbox-language/src/compiler/semantic.rs` is still the only one).
- `cargo test --workspace`: still exactly 117 tests passing, including
  `maltoolbox-attackgraph`'s partial-regeneration suite (the existing
  `AssetSnapshot`/`RemovedAssetSnapshot` consumer) - confirms the
  rename + field addition is genuinely additive, not a behavior change,
  for that caller.
- `maturin develop` rebuild installs cleanly (same known workaround:
  copy the built `.so` into `maltoolbox/`).
- **Exact reproduction of the two tests this gap was blocking**, run
  directly against the native bindings (not just reasoned about):
  - `test_model_remove_asset_with_association`'s full scenario
    (two assets, `hostApp`/`appExecutedApps` association, remove one,
    check both sides' `associated_assets` read back `{}`, check
    membership in `model.assets.values()`) - **passes**.
  - A second check: `hash`/`__eq__`/set-collapse on a tombstoned handle
    - still correct, since `__hash__`/`__richcmp__` only ever use
    `(owner ptr, id)` and never needed to resolve the asset's data in
    the first place.
- `uv run pytest tests/test_model.py -v`: 22/22 pass (pure-Python
  backend, unaffected - this phase didn't touch any `.py` file).
  `uv run pytest tests -m "not integration"`: 107 passed, 3 deselected
  - identical to every prior baseline in this effort, no regressions.

**Phase 2 is now genuinely, fully complete.**

**Next step:** implement the above, verify
`test_model_remove_asset_with_association` passes against the native
bindings without regressing anything else, then close out Phase 2 in
Phasing. After that, Phase 3 (`AttackGraph`/`AttackGraphNode`), which
needs its own `Option<Py<PyModel>>` back-reference design (already
decided) and is where the deferred `Model`/`AttackGraph` pickling work
(Phase 2 decision 3) actually lands.
