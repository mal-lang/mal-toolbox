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
  maltoolbox-model-py/      - PyModel, PyModelAsset
  maltoolbox-attackgraph-py/- PyAttackGraph, PyAttackGraphNode, PyDetector
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
- **Superseded by Phase 4 decision 1 - left here for history, see Status
  for the correction.** "Child" objects (`ModelAsset`, `AttackGraphNode`)
  were originally designed as **handles**, not copies and not cached:
  `PyModelAsset { owner: Rc<RefCell<Model>>, id: i64 }`,
  `PyAttackGraphNode { owner: Rc<RefCell<AttackGraph>>, id:
  AttackGraphNodeId }`. Every method borrows `owner` transiently and
  looks the item up by id. Constructing a fresh handle is just an `Rc`
  clone - cheap, so the original plan was that **no handle cache is
  needed for mutation visibility** (two handles for the same id already
  see each other's mutations, since they deref the same `RefCell`).
  Phase 4 found this incomplete: `tests/attackgraph/
  test_attackgraph.py::test_attackgraph_deepcopy` asserts
  `id(same_node) == id(node)` across two *separate* attribute accesses
  (not just post-deepcopy) and `id(original_node.model_asset) ==
  id(node.model_asset)` - real, existing, pre-Phase-4 test assertions
  that depend on repeat access to the same id returning the identical
  Python object, which an always-fresh handle can never satisfy. See
  Phase 4 decision 1 for the fix (a per-owner handle cache after all,
  applied retroactively to every handle type built so far).
- What a handle cache *would* have bought - and the cheaper fix originally
  used instead - is `dict`/`set` keying. CPython's default `__eq__`/
  `__hash__` for a type with neither overridden is identity-based, so
  two freshly-built handles for the same logical node would otherwise
  compare unequal. Confirmed via mal-simulator that this matters
  (`dict[AttackGraphNode, float]`). Fix: implement `__richcmp__`/
  `__hash__` on `PyModelAsset`/`PyAttackGraphNode` keyed on `(owner
  pointer identity via Rc::as_ptr, stable id)`, not on Python object
  identity. This remains correct and in place - the Phase 4 cache is
  additive on top of it (a cache hit returns the same object without
  needing `__richcmp__`/`__hash__` to run at all; a cache miss still
  needs them for the freshly-built handle to compare correctly against
  anything already in a `set`/`dict`).
  - ~~Known, accepted gap: `node_a is node_b` for two separately-obtained
    handles to the same logical node is `False` here, vs. always `True`
    in pure Python (one live object graph there).~~ **Corrected by Phase
    4 decision 1**: this gap turned out not to be accepted after all -
    the grep behind this claim missed `test_attackgraph_deepcopy`'s
    `id()`-based assertions (it doesn't contain the word "is", so a
    grep for `is`-based comparison didn't surface it). Checked: neither
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

Plan (as originally written, before implementation): `__getstate__`/
`__setstate__` on each compat class, implemented in terms of the
already-correct `to_dict`/`from_dict`, bundling whatever's needed to
reconstruct `lang_graph` standalone. **Superseded by what was actually
built**: every type ended up using pyo3's `__reduce__` protocol instead
(functionally equivalent - still built on `to_dict`/`from_dict`, still
needs no original `.mal`/`.mar` file on disk - just the more
pyo3-idiomatic mechanism for types without a usable `#[new]`). Container
types (`LanguageGraph`/`Model`/`AttackGraph`) pickle via `__reduce__` +
a `_from_pickle_state` staticmethod target; handle types
(`AttackGraphNode`, and per Phase 4 decision 9,
`LanguageGraphAsset`/`LanguageGraphAttackStep`) pickle via `__reduce__`
delegating to an owner + id/name, resolved by a module-level
`#[pyfunction]` rebuild target. Done and tested - see the "Phase N
status" write-ups below for each type, and decision 9 above for a
pickling gotcha found late (temporary-owner reconstruction order
mismatch). `test_simulator_picklable`-equivalent conformance is covered
by this repo's own `test_pickle_*`/`test_*_pickle` tests per type, not a
literal port of that mal-simulator test.

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

### Packaging (Phase 5, done - see "Phase 5 status" below for the full writeup)

This was a deliberate, acknowledged break to the **build/release**
pipeline - never to the Python API surface:

- `pyproject.toml`'s `[build-system]` moved from `setuptools` to
  `maturin`. **Done.**
- `mal-toolbox` is now a compiled-extension package unconditionally
  (same category as `pydantic`/`polars`/`ruff`). Prebuilt wheels for
  common platforms via `maturin`+`cibuildwheel` are built in CI on tag
  push; building from sdist on an uncovered platform now requires a Rust
  toolchain, where it never did before. **Done**, though the
  cibuildwheel/rustup CI recipe itself hasn't yet been exercised by a
  real tag push - see "Phase 5 status".
- The local-dev blocker (getting `maturin`'s `module-name =
  "maltoolbox._native"` to install the compiled extension *inside* the
  existing `maltoolbox/` source directory automatically, instead of a
  wrong-location bare top-level `_native` package) is fixed: setting
  `python-source = "."` in `[tool.maturin]` was the whole fix. The manual
  `cp` workaround described in earlier phases' status sections no longer
  applies - `uv sync`/`uv run` rebuild the extension in place
  automatically. **Done.**

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
- [x] **Phase 3 - `AttackGraph`/`AttackGraphNode`.** New
  `maltoolbox-attackgraph-py` crate. `PyAttackGraph(Rc<RefCell<
  AttackGraph>>)` **plus** the `Option<Py<PyModel>>` back-reference for
  `.model`. `PyAttackGraphNode` handle (owner + `AttackGraphNodeId`, no
  cache), `__richcmp__`/`__hash__` by `(owner ptr, id)`. This is where
  the pickling design actually gets implemented and tested (`AttackGraph`
  is what mal-simulator pickles). `AttackGraphException` family.
- [x] **Phase 4 - cut over.** Replace `maltoolbox/{model,language/
  languagegraph,attackgraph/{attackgraph,node}}.py` with thin
  re-export shims pointing at `maltoolbox._native`. Keep shims (not an
  immediate hard delete) until Phase 6's gate passes, then delete the
  superseded pure-Python logic outright. **Done** (4a: handle caching/
  model-effects/tombstone retrofit; 4b: the actual shim cutover, plus
  decisions 8-10 found along the way). Full suite green: 99 passed, 3
  deselected, 0 failed; `ruff`/`mypy` clean.
- [x] **Phase 5 - packaging.** `maturin` build backend, `python-source`
  wiring so the extension lands inside `maltoolbox/` properly (see
  "Packaging" above), `cibuildwheel` CI config, sdist-requires-Rust
  documented in README. **Done** - see "Phase 5 status" for the full
  writeup, including one not-yet-exercised item (the cibuildwheel/rustup
  recipe needs a real push to confirm it actually works end to end -
  `on: push` with no tag filter, kept identical to `main`, so any push
  exercises it).
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

## Phase 3 decisions (settled before implementation started)

Asked the user before writing code, same as Phases 1-2. Two genuine
architecture forks surfaced by grepping a fresh clone of
mal-simulator's `main` branch (not assumed - see each decision for the
exact call sites found); everything else below follows mechanically
from decisions already made in Phases 1-2.

1. **Detectors must be genuinely live, externally-mutable containers -
   confirmed necessary, not assumed.** Cloned mal-simulator fresh and
   found `tests/test_event_logger.py::test_logger_attacks_false_negative`
   does `app1_exploit.detectors['logExploit'] = Detector(name=..., node=...,
   potential_context=..., tprate=0.1)` (raw dict item-assignment on a
   node) and `test_logger_attacks_false_positive` does
   `scenario.attack_graph.detectors.remove(old); scenario.attack_graph
   .detectors.append(mocked_detector)` (raw list mutation on the graph) -
   and both tests then run a real simulation and assert on the resulting
   logs, so the mutation must actually take effect, not just not-crash.
   Also confirmed: `Detector` itself is imported and constructed directly
   by mal-simulator (`from maltoolbox.attackgraph import Detector`), so
   it needs a real public constructor, not just a to-dict-only value
   type. Also confirmed via `grep`: the Rust core has **no graph-level
   detectors list at all** - `AttackGraph` (graph.rs) has no `detectors`
   field; `generate_graph`/`create_detectors` only ever populate each
   node's own `detectors: HashMap<String, Detector>`, write-once at
   generation time, never read back afterward by anything in the core.
   Python's flat `AttackGraph.detectors: list[Detector]` is a separate,
   redundant, independently-mutable list that happens to start out
   containing the same `Detector` objects as every node's dict but is
   **never kept in sync with it afterward** (confirmed by reading
   `generate.py`: `detectors.extend(node_detectors.values())`, no link
   back) - the two false-negative/false-positive tests above each
   mutate only one of the two containers, never both, consistent with
   this.
   **Decision: compat-layer-owned live Python containers (not a
   write-through wrapper over a new core field).** `PyAttackGraph`/
   `PyAttackGraphNode` hold real, persistent `Py<PyDict>`
   (per node, keyed by detector label) / `Py<PyList>` (graph-level)
   objects, seeded once from the Rust core's generation-time detector
   data (full `generate_graph` and the newly-created nodes from
   `partially_regenerate_graph`) and from then on treated as the sole
   source of truth - the Rust core's own per-node `HashMap` is never
   consulted again after that initial seed. The two containers are
   deliberately left unsynchronized with each other, exactly matching
   Python's real (redundant) behavior confirmed above. Rejected
   alternative: add a `detectors: Vec<Detector>` field to the Rust
   core's `AttackGraph` struct and build custom Python Mapping/Sequence
   write-through wrapper types over both core-side containers - this
   would mean adding a field to the "clean" Rust core whose only purpose
   is accommodating Python's own redundant/unsynchronized data model
   (not a genuine Rust-side need), for substantially more implementation
   work (two protocol types instead of plain Python containers) with no
   behavioral difference. `PyDetector` itself needs a full `#[new]`
   constructor (`name`, `node: &PyAttackGraphNode`, `potential_context:
   dict[str, set[PyAttackGraphNode]]`, `tprate=None`, `fprate=None`) -
   this is unproblematic (unlike Phase 1's freeform-construction
   finding) since it only ever wraps a reference to an *existing* node
   handle, never needs detached/self-contained construction.
2. **`AttackGraph.nodes`/`.full_name_to_node` are real simulation
   hot-path attributes - confirmed necessary, not assumed.** Grepped a
   fresh mal-simulator clone: `sim_state.attack_graph.nodes[node.id]`
   appears in per-step assertions in `attacker_step.py`/
   `defender_step.py`/`dyna_mal_simulator/{attacker,defender}_step.py`
   (four call sites, each on the hot per-agent-per-step path), and
   `.nodes.values()` is iterated when building observation spaces
   (`envs/graph/utils.py`, `envs/graph/mal_spaces.py`,
   `policies/utils/path_finding.py`, `config/node_property_rule.py`).
   Unlike `LanguageGraph.assets`/`Model.assets` (Phases 1-2's "rebuild a
   real `dict` fresh on every access" precedent - fine there, since
   those are small, read rarely, and never used for single-key lookups
   in a loop), attack graphs can have thousands of nodes and this
   attribute is read on every simulation step, including via plain
   single-key indexing (`.nodes[id]`) that would otherwise pay an O(n)
   handle-construction cost just to do one O(1) lookup.
   **Decision: a custom, read-only, lazy Mapping-protocol pyclass**
   (`__getitem__`/`__len__`/`__contains__`/`__iter__`/`values()`/
   `keys()`/`items()`) backed directly by the Rust core's `id_to_node`
   map, constructing a `PyAttackGraphNode` handle only for key(s)
   actually touched rather than materializing the whole dict upfront on
   every access. Behaves like `dict[int, AttackGraphNode]` for every
   access pattern found in mal-toolbox's own tests and mal-simulator.
   Rejected alternative: keep the simple rebuild-fresh-dict-every-access
   pattern and defer to Phase 6's real run to reveal whether it's
   actually a practical problem - rejected because the hot-path call
   sites above are concrete and already confirmed, not speculative, so
   there's no real uncertainty left to resolve by waiting.
   `.full_name_to_node` (lower, non-hot-path usage - one test file reads
   `.keys()`/`.items()` directly) and `.attack_steps`/`.defense_steps`
   (3x/1x usage, always full iteration not indexed lookup) don't need
   this treatment - left as the simple rebuild-fresh-collection pattern,
   reusing the lazy wrapper only if it turns out to be free to do so.
3. **Node/asset/step handle ownership: `owner_py: Py<PyAttackGraph>`,
   not a bare `Rc<RefCell<AttackGraph>>`.** Not asked as a question
   (judged a clear win on every axis, same category as Phase 2 decision
   4). `PyAttackGraphNode.model_asset` needs to build a `PyModelAsset`
   handle (requires reaching the owning `PyModel`) and `.lg_attack_step`
   needs to build a `PyLanguageGraphAttackStep` handle (requires
   reaching the owning `PyLanguageGraph`) - so the node handle needs
   access to `PyAttackGraph`'s own `model_py`/`lang_graph_py` fields
   regardless. Storing a single `owner_py: Py<PyAttackGraph>` (deriving
   the core `Rc<RefCell<AttackGraph>>` via `owner_py.borrow(py).inner`
   each access, same transient-borrow pattern as every other handle)
   is simpler than separately threading three fields through node
   construction, *and* it makes node pickling fall out almost for free
   (see decision 4) - not a tradeoff worth asking about.
4. **Pickling: dict-based `__getstate__`/`__setstate__`, reusing
   `_to_dict`/`from_dict`, with handle pickling delegating to
   `(owner_py, id)`.** This is the pickling design Phase 2 decision 3
   deferred to this phase. Confirmed via a fresh mal-simulator clone
   that the only real assertion any pickling test makes post-round-trip
   is `_to_dict()`/`to_dict()` equality (`test_simulator_picklable`,
   `test_scenario_pickle`) - never object identity - which is the bar
   this design targets, not full object-graph fidelity.
   - `PyLanguageGraph`/`PyModel`/`PyAttackGraph` each get
     `__getstate__`/`__setstate__` built from their already-correct,
     oracle-verified `_to_dict()`/`from_dict()` pair (`PyAttackGraph`'s
     state bundles its own `_to_dict()` plus its nested `model`'s and
     `lang_graph`'s, so unpickling can rebuild the whole chain
     bottom-up with no on-disk file needed).
   - Handle types (`PyAttackGraphNode`, and by the same mechanism
     `PyModelAsset`/`PyLanguageGraphAsset`/`PyLanguageGraphAttackStep` -
     confirmed via grep that mal-simulator pickles bare `AttackGraphNode`
     instances directly as members of frozen-dataclass `Set`/`Mapping`
     fields, e.g. `AttackerState.entry_points: Set[AttackGraphNode]`,
     `DefenderState.compromised_nodes: Set[AttackGraphNode]`, both with
     their own `__getstate__` that round-trips these sets as-is) pickle
     via `__reduce__` returning `(rebuild_fn, (self.owner_py, self.id))`
     rather than snapshotting their own data. This is not just simpler
     than a standalone-snapshot design, it's *more correct*: because
     `owner_py` is a real, identity-stable `Py<PyAttackGraph>` object,
     pickling it is automatically memoized by Python's own pickle
     protocol - if the same `AttackGraph` is reachable from multiple
     places in one combined pickle call (e.g. `MalSimulator.sim_state
     .attack_graph` *and* a `DefenderState.compromised_nodes` node's
     `owner_py`, both present in the same `pickle.dump` call per
     `test_simulator_picklable`'s `MALSimulatorStaticData`/
     `MalSimulatorState` shapes), pickle serializes the graph once and
     both references correctly restore pointing at the *same* object,
     for free, with no bespoke identity-tracking code needed here.
5. **Not a Phase 3 blocker, flagged for Phase 4**: `tests/attackgraph/
   test_partial_regeneration.py` tests several *internal* module-level
   functions directly (`assoc_affected_expr_chain`, `assoc_left_assets`,
   `correct_node_children_on_modified_assoc`, `nodes_to_be_removed`,
   each with hand-built `ExpressionsChain(...)`/detached
   `AttackGraphNode(...)` instances, not going through any `AttackGraph`
   container). These aren't part of the public `AttackGraph`/
   `AttackGraphNode` API surface at all - they're
   `maltoolbox/attackgraph/partially_generate.py`'s own private helpers,
   which have no PyO3-bound equivalent (only the public
   `AttackGraph.partially_regenerate_graph` method is bound; the Rust
   core's own internal equivalents in `partially_generate.rs` are
   already covered by the existing 117-test workspace suite). This
   doesn't block Phase 3 - nothing here is cut over yet, so these tests
   still run unmodified against the still-intact pure-Python module -
   but it means these specific tests have no path to "keep passing"
   once Phase 4 deletes `maltoolbox/attackgraph/partially_generate.py`
   in favor of the native binding, and will need an explicit call
   (delete, since the Rust-side logic they exercise is independently
   tested already) when that phase starts.

## Phase 4 decisions (settled before implementation started)

Asked the user before writing code, same as Phases 1-3. One of these
(decision 1) is a genuine correction to an architecture call made back
in Phase 1 and relied on through Phase 3 - not a new tradeoff, a bug in
earlier due diligence that real existing tests exposed.

1. **Per-owner handle cache: `node_a is node_b` must be `True` for two
   separately-obtained handles to the same logical object within the
   same owner - the "no cache needed" call from Phase 1's Architecture
   section was wrong, not just incomplete.** Found while researching
   Phase 4 (not assumed, not reported by the user from memory -
   confirmed by directly reading the test): `tests/attackgraph/
   test_attackgraph.py::test_attackgraph_deepcopy` asserts
   `id(same_node) == id(node)` where both are obtained via two
   *separate* `attack_graph.nodes[node.id]` lookups (not a deepcopy
   artifact - this would fail even with no `__deepcopy__` call anywhere
   in the test), and `id(original_node.model_asset) ==
   id(node.model_asset)` similarly for `ModelAsset`. The user then
   confirmed this independently and explained the real-world
   consequence: mal-simulator relies on node identity (not just
   `__eq__`/`__hash__`) for correctness, so this is not a test
   artifact to work around - it's a real requirement. Phase 1's
   "known, accepted gap" writeup was based on a grep for `is`-based
   comparisons, which missed this because the assertions use `id(...)
   ==`, not the `is` keyword - a methodology gap in that earlier
   check, not a change in the facts.
   **Decision: implement a per-owner handle cache** -
   `HashMap<id, Py<Handle>>` stored on each container (`PyLanguageGraph`,
   `PyModel`, `PyAttackGraph`), so repeated lookups for the same id
   within the same owner return the *identical* Python object, while
   two different owner instances (even structurally-identical ones,
   e.g. a deepcopy) never share identity - matching the "same id, same
   owner -> same object; different owner -> always a different object"
   behavior the user asked for exactly. This is implemented as a cache
   *in addition to*, not instead of, the existing `__richcmp__`/
   `__hash__` scheme (owner-ptr+id keyed) from Phase 1 - the hash/eq
   impl still matters for a cache miss (freshly-built handle comparing
   against something already in a `set`/`dict`) and for cross-owner
   comparisons (which the cache deliberately doesn't unify). Confirmed
   this also matches Python's actual memory behavior more closely than
   the no-cache design did, not just test expectations: in pure Python,
   every node already lives forever in `AttackGraph.nodes`'s own dict,
   so a cache that keeps every *accessed* node alive for the owner's
   lifetime isn't a new memory-retention behavior, just catching up to
   what was already true.
   **Decision: apply uniformly to all four handle types now**
   (`PyLanguageGraphAsset`, `PyLanguageGraphAttackStep` - Phase 1;
   `PyModelAsset` - Phase 2; `PyAttackGraphNode` - Phase 3), not just
   the two (`PyModelAsset`/`PyAttackGraphNode`) with a confirmed
   reproducing test. Rationale: the only reason Phase 1's two types
   don't have a confirmed-failing test today is that Phase 1's own test
   suite never happened to exercise this pattern for them - the same
   gap-in-the-original-grep logic that missed `test_attackgraph_deepcopy`
   means absence of a known failure isn't evidence of absence of the
   problem. Leaving two of four handle types on a different identity
   model than the other two would also be a real, confusing
   inconsistency in the binding layer itself.
   **Implementation shape**: each container gains a
   `handle_cache: Rc<RefCell<HashMap<IdType, Py<HandleType>>>>` (or
   equivalent per-type storage - `PyLanguageGraph` needs two, one for
   assets keyed by `AssetId` and one for attack steps keyed by
   `AttackStepId`). Every method that currently constructs a fresh
   handle (getters, `get_node_by_full_name`, `add_asset`, iteration via
   the lazy `.nodes` view, etc.) changes to "look up in the cache first,
   construct-and-insert on a miss" instead of "always construct". On
   removal (`Model.remove_asset`, `AttackGraph.remove_node`/partial
   regeneration's internal removals), the cache entry is **not**
   evicted outright - see decision 4 below for why keeping it (pointing
   at a tombstoned/removed-but-still-readable state) is actually the
   right behavior, not a leak: a Python caller already holding that
   exact object reference keeps seeing a stable, readable, if
   post-removal, object - matching Python's real behavior of "removed
   from the dict, but the object itself lives on unchanged" even more
   closely than before.
2. **The 8 internal-function tests in `test_partial_regeneration.py`
   get deleted**, not kept via a permanently-uncut-over
   `partially_generate.py`. Confirmed scope by reading the file: exactly
   8 of 16 tests (`test_switch_fieldname_unknown_fieldname_raises`
   onward) call `assoc_affected_expr_chain`/`assoc_left_assets`/
   `correct_node_children_on_modified_assoc`/`nodes_to_be_removed`/
   `switch_fieldname` directly with hand-built `ExpressionsChain`/
   detached `AttackGraphNode` objects; the other 8 (`test_partial_regeneration`
   through `test_partial_regeneration_shared_assoc_sibling`) only exercise
   the public `AttackGraph.partially_regenerate_graph` method and are
   unaffected by this decision either way. Equivalent coverage already
   exists independently in `crates/maltoolbox-attackgraph/tests/
   test_partial_regeneration.rs` (9 of its own `#[test]`s). Rejected
   keeping `partially_generate.py` around forever just to keep these 8
   tests passing unmodified - would mean carrying dead pure-Python logic
   that duplicates (and could silently drift from) the Rust
   implementation, for a module nothing else calls once
   `AttackGraph.partially_regenerate_graph` is native-backed.
3. **Build the full `additive_model_effects`/`subtractive_model_effects`
   wrapper hierarchy now, not deferred further.**
   `tests/attackgraph/test_attackgraph.py::test_create_dynamic_ag`
   exercises this in real structural depth (`.base[i].field_name`,
   `.targets[i].assoc_traversal[j].asset_filter.name`,
   `.targets[i].assoc_op`, etc.) against a real DynaMAL language
   (`tests/testdata/wiperLang.mal`) - confirmed this needs genuine
   `PyLanguageGraphModelEffect`/`PyAssocTraversal`/
   `PyGlobAssocTraversal`/`PyAssocSet`/`PyDynTarget` wrapper classes
   (mirroring `maltoolbox/language/language_graph_model_effect.py`'s
   `LanguageGraphModelEffect`/`AssocTraversal`/`GlobAssocTraversal`/
   `AssocSet`/`DynTarget`/`ModelEffectType`), not a quick shim. Rejected
   skipping/adjusting the test and deferring again - would carve out an
   explicit, known exception to "the existing test suite keeps passing"
   right at the one phase where that stops being optional, for a
   DynaMAL-relevant feature a downstream consumer could plausibly use.
4. **Build the `AttackGraphNode` post-removal tombstone proactively
   now**, mirroring Phase 2's `AssetSnapshot` mechanism, even though no
   test reproduces the gap today (`test_attackgraph_remove_node` only
   does membership checks, never reads a removed node's attributes).
   Decision 1's per-owner cache raises the real-world odds of this
   mattering: previously, every node access was a disposable fresh
   handle, so "does a removed node's handle stay readable" rarely came
   up in practice; now that the same Python object is handed out
   repeatedly and plausibly held onto externally (e.g. a `compromised_nodes`
   set surviving a later partial regeneration that removes that node),
   hitting this gap for real is materially more likely than it was
   before this phase's other decisions.
5. **The MAL compiler itself (`maltoolbox/language/compiler/`,
   `mal_analyzer.py`) stays pure Python permanently - not asked as a
   question, judged a clear win, same category as Phase 2 decision 4.**
   `tests/language/test_compiler.py` constructs and calls `MalCompiler()`
   directly (not via `LanguageGraph.from_mal_spec`) and asserts on raw
   tree-sitter AST shape (`PARSER.parse(...)`, `node.type`, `node.children`)
   - binding a tree-sitter AST object through PyO3 would be a large,
   separate project serving no goal this effort actually has (the Goal
   section's "every one of those classes" refers to the five originally-
   named classes - `LanguageGraph`/`Model`/`ModelAsset`/`AttackGraph`/
   `AttackGraphNode` - not the compiler). `LanguageGraph.from_mal_spec`/
   `from_mar_archive` already route through the Rust core's own,
   separate compiler implementation and already have full exception
   parity (Phase 1 decision 3) - the two compilers (pure-Python
   `MalCompiler`, used only when called directly; Rust, used only via
   `LanguageGraph`) coexisting permanently, never sharing an
   implementation, is the correct end state, not a temporary gap.
6. **Added mid-Phase-4b, found by real test failure, not anticipated by
   decision 5 above: `maltoolbox/language/compiler/exceptions.py` (and
   `mal_analyzer.py`'s `malAnalyzerException`) become thin re-export
   shims pointing at `_native.language.compiler.exceptions`/
   `_native.language.compiler.mal_analyzer`, even though the compiler's
   actual parsing/analysis *logic* stays pure Python per decision 5.**
   Found via `tests/language/test_detectors.py::test_wrong_labels`:
   it imports `MalCompilerError` from the pure-Python
   `maltoolbox.language.compiler.exceptions` module and wraps a call to
   `LanguageGraph.from_mal_spec(...)` (native, post-cutover) in
   `pytest.raises(MalCompilerError)` - but the native path raises
   `_native`'s own `MalCompilerError`, a genuinely different Python
   class object despite Phase 1 having cosmetically set its `__module__`
   to the same string for pickling purposes (see Phase 1's exceptions.rs
   notes) - `pytest.raises` doesn't catch it, since Python exception
   matching is real `isinstance`, not string/module-name comparison.
   Decision 5 only considered the standalone `MalCompiler()` call path
   (`test_compiler.py`, which doesn't care about the specific exception
   class), not this combination. **Resolved by shimming just the
   exception *classes*** (not the compiler itself) to the already-
   registered native submodules - both `MalCompiler()` (now raising via
   the shimmed-to-native classes) and `LanguageGraph.from_mal_spec` end
   up raising/catching the identical class, while the two compilers'
   actual implementations remain fully separate and unshared, preserving
   decision 5's core point.
7. **Deterministic, Python-matching node generation order: `HashMap` ->
   order-preserving map for `LanguageGraphAsset.attack_steps`/
   `own_associations`/`own_variables` (`crates/maltoolbox-language/src/graph/asset.rs`)
   - not asked as a question, judged a clear win given existing project
   precedent.** Found via real test failures, not anticipated: `tests/
   attackgraph/test_attackgraph.py::test_attackgraph_according_to_corelang`
   asserts a *specific* node (`attack_graph.nodes[0]`) has a specific set
   of children by name - this only holds if fresh generation assigns the
   same node to id `0` Python does, which requires asset attack-steps to
   be iterated in MAL-declaration order during generation
   (`crates/maltoolbox-attackgraph/src/generate.rs::create_nodes_for`
   does `model.lang_graph.asset(..).attack_steps.values().copied()
   .collect()` - a `HashMap`, so this iterates in random, per-process
   hash order, not declaration order). `tests_create_ag_step_lists`
   (order mismatch between `created_ag.nodes.values()`-filtered-by-type
   and `created_ag.defense_steps`) is the same root cause manifesting a
   second way. This is the same gap Phase 3 status already logged
   ("fresh `generate_graph` node-id numbering isn't guaranteed to match
   Python's... no observable effect on correctness") - that assessment
   was wrong for the cutover scenario specifically, the same way earlier
   "no usage found" claims (identity comparisons, `LanguageGraphAttackStep
   .detectors`) turned out wrong once real tests ran against the native
   bindings instead of being reasoned about from a grep.
   **Decision: switch the three listed `HashMap` fields to an
   order-preserving map** (`indexmap::IndexMap` - already transitively
   present in `Cargo.lock`, most likely pulled in by `serde_json`'s
   `preserve_order` feature the workspace already enabled for the exact
   same reason: `Cargo.toml` already states `serde_json = { features =
   ["preserve_order"] }`, specifically "to match Python's
   dict-order-dependent wire format" per `PORTING_NOTES.md`'s own
   "JSON key order" row). This isn't a new tradeoff being introduced -
   it's extending a principle this project already committed to, to a
   place that turned out to need it too. `IndexMap`'s API is a drop-in
   `.values()`/`.keys()`/indexing replacement for `HashMap`, so the
   blast radius through the rest of the core crate should be small -
   confirm this by actually making the change and running the full
   workspace test suite, not assumed.

8. **Detached `AttackGraphNode` construction + `AttackGraph(None)` + a `.nodes` setter** (found and decided during Phase 4b's resumption, not asked up front - confirmed real via the pure-Python originals, not a test-rewrite situation). `git show HEAD:maltoolbox/attackgraph/{attackgraph,node}.py` confirms three `tests/patternfinder/test_attackgraph_patterns.py` tests plus `test_attackgraph_generate_graph` rely on real historical behavior: `AttackGraph.nodes` was a plain, freely settable `dict` attribute, and `AttackGraphNode.__init__(node_id, lg_attack_step, model_asset=None, ttc_dist=None, existence_status=None, full_name=None)` could always be called directly to build a fully standalone node (mutable `.children`/`.parents`, no owning graph) - needed so `patternfinder`'s algorithm can be tested against hand-built tiny graphs without a real `Model`/`LanguageGraph`. Implemented by giving `PyAttackGraphNode` (`python/maltoolbox-attackgraph-py/src/node.rs`) a `NodeRepr` enum - `Owned { owner_py, id }` (the existing, unchanged cached-handle behavior) or `Detached(DetachedNode)` (a self-contained struct holding `children`/`parents` as plain mutable `Py<PySet>` fields). Scope deliberately narrow: `Detached` only implements what `maltoolbox/patternfinder/attackgraph_patterns.py` actually reads - `__init__`, `.id`, `.name`, `.children`/`.parents` (get+set), `__repr__`, and default identity-based `__hash__`/`__richcmp__` (matching the original Python class's lack of custom equality); everything else (`to_dict`, pickling, model-effects getters, `Detector` construction) returns `NotImplementedError` for a `Detached` node. `PyAttackGraph::new` now accepts `lang_graph: Option<...>`; `None` builds a minimal placeholder `LanguageGraph` internally (via the same `generate_graph(json!({}))` code path a genuinely empty MAL language would use) rather than threading `Option` through every other field/method. `PyAttackGraph` gained `nodes_override: Rc<RefCell<Option<Py<PyDict>>>>`: when set (via the new `.nodes` setter), the `.nodes` getter returns it directly instead of constructing the usual lazy `PyAttackGraphNodesView`; `regenerate_graph` resets it to `None`, so `attack_graph.nodes = {}` followed by `regenerate_graph()` correctly reverts to live, freshly-generated nodes afterward.

9. **`LanguageGraphAsset`/`LanguageGraphAttackStep` pickling via a temporary owner, not stored identity** (found and decided during Phase 4b's resumption). `test_pickle_languagegraph_asset`/`test_pickle_languagegraph_attack_step` only assert `to_dict()` equality after a round-trip, not object identity - unlike `AttackGraphNode`, these two handle types don't need the heavier "store a real `owner_py: Py<Self>` field" treatment (Phase 3 decision 3). Both already carry `owner: Rc<RefCell<LanguageGraph>>` + `caches: SharedLangGraphCaches` (both `pub`, same crate as `PyLanguageGraph`), so `__reduce__` constructs a *fresh, temporary* `PyLanguageGraph { inner: self.owner.clone(), caches: self.caches.clone() }` (the same underlying `Rc`, not a copy) wrapped in `Py::new` purely for the pickle call, and delegates to it - pickle recursively pickles that temporary owner via `PyLanguageGraph`'s own existing `__reduce__`, no new graph-serialization logic needed. The id itself round-trips through slotmap's `KeyData::as_ffi()`/`from_ffi()`. **Caveat discovered during verification, not anticipated when this decision was first written down:** `PyLanguageGraph`'s own `__reduce__` doesn't just re-wrap the same live `Rc` on unpickling - it serializes to `_to_dict()` and reconstructs an entirely new `LanguageGraph` via `language_graph_from_dict` (`crates/maltoolbox-language/src/graph/file.rs`), a *different* code path from the normal `generate_graph(lang_spec)` build. For `LanguageGraphAsset` this happened to not matter (asset insertion order matches between the two paths), but for `LanguageGraphAttackStep` it did not: `language_graph_from_dict` builds attack steps in a different global order (own-then-inherited across all assets) than `generate_graph` (own-and-inherited per asset, one asset at a time), so a step's raw slotmap id from the original graph can land on a *different* step in the reconstructed one - same logical graph, different internal ids. Fixed by pickling attack steps by `(asset_name, step_name)` instead of the raw ffi id (assets keep using the ffi id, since their round-trip is unaffected). If a similar pickling need ever arises for `own_associations`/`own_variables`, check this ordering divergence first rather than assuming the ffi-id approach is safe by default.

10. **`LanguageGraphAttackStep.detectors` exposure via a new `python/maltoolbox-language-py/src/detector.rs`** (found and decided during Phase 4b's resumption). `tests/language/test_detectors.py::test_only_tpr`/`test_only_fpr` need `.detectors: dict[str, LanguageGraphDetector]` on attack steps; the pure-Python original's exact dataclass shapes were recovered via `git show HEAD~30:maltoolbox/language/language_graph_detector.py` (deleted this phase): `LanguageGraphDetector { name, context: dict[str, LanguageGraphContextItem], type, tprate=1.0, fprate=0.0 }` / `LanguageGraphContextItem { label, asset_type: LanguageGraphAsset, attack_step_name, expr: ExpressionsChain | None }`. The Rust core already had everything needed (`crates/maltoolbox-language/src/graph/detector.rs`'s `LanguageGraphDetector`/`LanguageGraphContextItem`, populated on `LanguageGraphAttackStep.detectors`) - just needed a pyo3 wrapper. New `PyLanguageGraphDetector`/`PyLanguageGraphContextItem` mirror `model_effect.rs`'s established pattern exactly (Phase 4 decision 3's scope relaxation applies identically here: plain, freely-constructible value snapshots, no identity caching/`__richcmp__`/`__hash__`), with `asset_type` resolving to a real cached `PyLanguageGraphAsset` handle the same way `model_effect.rs`'s `cached_asset` does. Wired in as a new `#[getter] fn detectors` on `PyLanguageGraphAttackStep` (`attack_step.rs`).

## Status

**Current phase: Phase 0 through 5 all done** - the public `maltoolbox`
package is fully native-backed (`maltoolbox/{model,language/
languagegraph,attackgraph/{attackgraph,node}}.py` and the exception/
compiler-exception modules are thin re-export shims over
`maltoolbox._native`), with the full verification bar green (99 passed,
3 deselected, 0 failed; `ruff`/`mypy` clean), and the build now goes
through `maturin` end to end - `uv sync`/`uv run` rebuild the extension
in place with no manual `cp` step. See "Phase 4a status", "Phase 4b
status", and "Phase 5 status" below for the full writeups. Next: Phase 6
(mal-simulator acceptance gate) - not started, paused per the user's
standing instruction to check in before proceeding past each phase.

### Phase 4a status: handle caching retrofit, model effects wrapper, node tombstone (done)

Implements Phase 4 decisions 1, 3, and 4 - strengthens the native
binding crates themselves; does **not** touch any `maltoolbox/*.py` file
or wire the native module into the public package (that's Phase 4b).

**Decision 1 (per-owner handle cache), implementation shape:**
- New shared infra in `python/maltoolbox-language-py/src/handle.rs`:
  `HandleCache<K, V> = Rc<RefCell<HashMap<K, Py<V>>>>`,
  `new_handle_cache()`, and `cached_handle(cache, py, key, build)` -
  looks up `key`, returns the cached `Py<V>` via `clone_ref` on a hit,
  else builds fresh via `build()` (only called on a miss), wraps it,
  inserts it, and returns it. Also `LangGraphCaches` (bundles the
  `AssetId`/`AttackStepId` caches a `LanguageGraph` needs into one `Rc`,
  so every type that needs to build asset/step handles - including
  cross-crate consumers - threads one field, not two).
- **All four handle types retrofitted**, not just the two
  (`PyModelAsset`/`PyAttackGraphNode`) with a confirmed failing test:
  `PyLanguageGraphAsset`/`PyLanguageGraphAttackStep` gained a
  `caches: SharedLangGraphCaches` field; `PyModelAsset` gained
  `handle_cache` (its own type's cache) plus `lang_caches` (so `.lg_asset`
  resolves through the same cache as every other path to that asset);
  `PyAttackGraphNode` didn't need a new field at all - it already held
  `owner_py: Py<PyAttackGraph>` (Phase 3 decision 3), so `PyAttackGraph`
  just gained a `node_cache` field and a `node_handle(&self, owner_py,
  py, id)` method every node-producing call site now goes through.
  `PyLanguageGraphAssociation`/`PyLanguageGraphAssociationField` (not one
  of the four cached types) also gained a `caches` field purely so their
  `.asset`/`.left_field.asset`/etc. getters resolve to the same cached
  asset handle as every other path - free consistency, not a scope
  expansion of what's cached.
- **Every existing handle-constructing call site updated** (getters,
  `add_asset`/`add_node`, the lazy `.nodes`/`PyAttackGraphNodesView`
  view, `partially_regenerate_graph`'s returned/created nodes,
  `Detector.node`/`PyDetector`'s own `#[new]` - now resolves the passed-in
  node through the cache rather than cloning the handle's own data
  detached, so `detector.node is the_node` holds) - verified via
  `grep`+recompilation (the compiler catches any missed site immediately,
  since `PyModelAsset::new`'s signature grew), not just reasoning about
  coverage.
- **id-reuse-after-removal eviction fix** (the concrete correctness
  hazard flagged in the dispatching prompt, confirmed real, not
  hypothetical): `Model::add_asset`/`AttackGraph::add_node` both accept
  an explicit caller-chosen id, and the core happily accepts one that
  collides with a *previously removed* id (`self.assets.contains_key`/
  `self.id_to_node.contains_key` correctly report it as free). Without a
  fix, `asset_handle(id)`/`node_handle(id)` would return the *stale,
  tombstoned* cached object for the old removed item instead of a fresh
  handle for the new one at that id - confirmed by direct reproduction
  before fixing it. Fixed with `PyModel::evict_handle`/
  `PyAttackGraph::evict_node_handle` (remove the cache entry, called only
  from `add_asset`/`add_node` right after a successful core-level add,
  never from removal itself - matching Phase 4 decision 1's explicit
  "don't evict on removal" guidance literally, since eviction here is
  about a *new* object legitimately claiming an old id, not about the
  removed object's own lifecycle).
- `regenerate_graph` (both the language-graph and attack-graph one)
  clears its cache(s) entirely - a full rebuild invalidates every old
  slotmap key regardless, so nothing in the old cache could resolve
  correctly afterward anyway.

**Decision 3 (model effects wrapper), implementation shape:**
- New `python/maltoolbox-language-py/src/model_effect.rs`: real
  (uncached, unhashable - per explicit user scope relaxation for these
  specific types, confirmed not needed since nothing compares/hashes
  them) wrapper pyclasses `AssocTraversal`/`GlobAssocTraversal`/
  `AssocSet`/`DynTarget`/`LanguageGraphModelEffect`, converting the core's
  existing `maltoolbox_language::graph::model_effect` types (which
  already had a complete, tested Rust implementation - this was a
  binding task, not a port). `AssocTraversal.asset_filter` resolves
  through the real `LangGraphCaches` (Phase 4 decision 1's cache) when
  present, for consistency with every other path to a
  `PyLanguageGraphAsset`.
- `PyAttackGraphNode.additive_model_effects`/`subtractive_model_effects`
  now return `Some(list[LanguageGraphModelEffect])`/`None` for real
  instead of raising `NotImplementedError` on the non-empty case.
- **Verified against the exact, full `test_create_dynamic_ag` scenario**
  (not a synthetic simplification): loaded `tests/testdata/wiperLang.mal`
  + `tests/testdata/wiper_model.yml` through the native bindings,
  reproduced every assertion from the real test line-for-line
  (`.base[0].field_name == "self"`, `.targets[i].assoc_traversal[j]
  .asset_filter.name`, the full model-mutation loop adding assets via
  `get_lg_assoc_field`/`add_associated_assets` and catching the
  max-cardinality `ValueError`, then `regenerate_graph()`) - passes
  end to end.
- **Real pre-existing bug caught and fixed along the way** (not
  introduced by this phase, not previously caught by any test or oracle
  diff): the model-mutation loop's cardinality-exceeded path raises
  `ModelError::TooManyAssetsInField`, whose `#[error(...)]` Display
  format used `{0:?}` on an `Option<i64>`, producing `"You can have
  maximum Some(1) assets..."` instead of Python's real `"You can have
  maximum 1 assets..."` - confirmed via a direct string-equality
  assertion against the real test's expected message. Fixed by changing
  the variant to store the already-unwrapped `i64` (the one construction
  site in `crates/maltoolbox-model/src/model.rs` only ever runs inside an
  `if let Some(max) = ...`, so the `Option` wrapper was never doing
  anything except making the Display output wrong) - flagged, narrow,
  and the one existing test referencing this variant
  (`matches!(err, ModelError::TooManyAssetsInField(..))`) doesn't
  inspect the inner value, so unaffected.

**Decision 4 (node tombstone), implementation shape - deliberately
partial, logged, not silently narrowed:**
- Core change: `AttackGraph::remove_node` (`crates/maltoolbox-attackgraph/
  src/graph.rs`) now returns `Result<AttackGraphNode, GraphError>` (the
  removed node's final state, cloned right before deletion - same
  capture-point convention as `AssetSnapshot::final_state`) instead of
  `Result<(), GraphError>`. The one other core call site
  (`partially_regenerate_graph`'s internal removal loop) already
  discarded the return value in statement position, so this didn't need
  updating; the test call site likewise.
- `PyAttackGraph` gained a `tombstones: Rc<RefCell<HashMap<i64,
  AttackGraphNode>>>` map, populated by `remove_node` (direct path) and
  by `partially_regenerate_graph` (side-effect-removal path - snapshots
  *every* node's full state before the core call, since there's no way
  to know in advance which ids a side-effect removal will claim, then
  diffs node-id-sets after the call the same way the existing
  detector-purge logic already did, to populate tombstones only for ids
  that actually disappeared).
- `PyAttackGraphNode` gained `with_node_value` (resolves to `&AttackGraphNode`
  directly, live-or-tombstoned - mirrors `PyModelAsset::with_asset`
  exactly) alongside the existing `with_node` (key-based, no tombstone
  fallback). **Tombstone coverage is deliberately partial**: `name`/
  `type`/`lg_attack_step`/`causal_mode`/`ttc`/`tags`/
  `additive_model_effects`/`subtractive_model_effects`/`model_asset`/
  `existence_status`/`extras`/`info` all go through `with_node_value` and
  are tombstone-covered. `full_name`/`to_dict`/`__repr__`/`children`/
  `parents`/`.detectors` do **not** get tombstone fallback - they
  ultimately call core functions that take a live slotmap key
  (`full_name_of`/`node_to_dict`/`detector_snapshots_for`) or need to
  cross-reference *other* (still-live) nodes, and extending those to
  accept a bare node value instead of a key is a larger core-crate change
  not attempted this pass. This scope line was a judgment call given no
  reproducing test exists for *any* of this (proactive work per Phase 4
  decision 4) - logged here rather than silently narrowed without
  mention.

**Verified** (matching Phases 1-3's rigor):
- `cargo build`/`cargo clippy --all-targets` clean on all three
  `python/` crates and the `maltoolbox-pyo3` umbrella - zero new
  warnings (one unrelated, pre-existing `redundant_guards` warning in
  `maltoolbox-language/src/compiler/semantic.rs` remains, same as every
  prior phase).
- `cargo build --workspace`/`cargo test --workspace`: still exactly 117
  tests passing (the `AttackGraph::remove_node` signature change and the
  `ModelError::TooManyAssetsInField` fix are both additive/non-breaking
  to every existing core-crate test).
- `maturin develop --release` builds/installs cleanly; same known
  wrong-install-location workaround as every prior phase.
- **Per-owner identity, reproduced directly for all four handle types**:
  fetched the same logical item two different ways within the same owner
  (`lg.assets['Application']` twice; `a1.attack_steps[name]` two
  different ways; `model.assets[id]` and `get_asset_by_name`;
  `ag.nodes[id]` and `get_node_by_full_name`) and confirmed `is` is now
  `True` in every case (previously `False` everywhere, by design, before
  this phase). Confirmed cross-owner non-sharing holds for all four too
  (a second, independently-constructed `LanguageGraph`/`Model`/
  `AttackGraph` never shares identity with the first, even for
  structurally-identical content).
- Dict/set keying re-verified post-retrofit (set-collapse to length 1)
  for all four types - confirms the cache didn't disturb
  `__richcmp__`/`__hash__`, which remain independent mechanisms.
- **id-reuse-after-removal, reproduced directly**: removed an asset/node
  at an explicit id, re-added a *different* logical asset/node at the
  same explicit id, confirmed the new handle is not the stale cached
  object and has the new object's correct data, and that *further*
  access to that id now consistently returns the new object.
- **Tombstone, reproduced directly**: removed a node via `remove_node`,
  confirmed a previously-held reference's `name`/`tags`/
  `existence_status` still read correctly afterward (the same scenario
  `test_model_remove_asset_with_association`'s `ModelAsset` analog
  exercises, now covered for nodes too, though - as logged above - with
  narrower getter coverage than the `ModelAsset` tombstone has).
- **Model effects, reproduced directly**: full `test_create_dynamic_ag`
  scenario end to end (see Decision 3 above).
- Oracle diffs re-run post-retrofit: `Model`/`ModelAsset` (2 assets, one
  association, before and after `remove_asset`) and `AttackGraph`
  (structural, 3 assets + 1 association, matching Phase 3's own
  methodology) both still match the untouched pure-Python
  implementation exactly.
- Live detector mutation (Phase 3 decision 1) and pickling
  identity-sharing (Phase 3 decision 4) both re-verified against the
  rebuilt `.so` - unaffected by this phase's changes, as expected, but
  confirmed rather than assumed.
- Full existing pytest suite unaffected - **no `.py` file was touched by
  this phase** (confirmed via `git status`): `uv run pytest tests -m
  "not integration"` - 107 passed, 3 deselected, identical to every
  prior baseline. `uv run ruff check .` - clean.

**Newly discovered, logged, not fixed (out of this phase's assigned
scope - caching/model-effects/tombstone, not pickling):** pickling an
`AttackGraph` through a real language-level detector
(`tests/testdata/detector_lang.mal`) loses the `detectors` key from
`_to_dict()`'s output for any node that had one - confirmed via direct
reproduction, with and without first mutating `.detectors`, so it's not
about the Phase 3 decision 1 live-mutation design, just about
`AttackGraph::from_dict` (and therefore `_from_pickle_state`, which
calls it) never reading `node_dict['detectors']` back - which,
per `PORTING_NOTES.md`'s existing documentation of
`attack_graph_from_dict`, is actually consistent with the real Python
original's own behavior (`node_dict['detectors']` is written by
`to_dict` but never read back by `_from_dict` there either). So this
isn't a new divergence from Python - it's a gap in Phase 3's own
pickling *verification*, which used a model with no language-level
detectors and therefore never exercised this path. Not fixed here since
it's outside this phase's assigned scope and isn't caused by anything
this phase changed; flagged for whoever next touches pickling or adds a
`test_attackgraph_pickle`-style conformance test using a detector-bearing
language (worth doing before Phase 6, since `tests/attackgraph/
test_attackgraph.py::test_attackgraph_pickle` is a real *existing*
pure-Python test Phase 4b's cutover needs to keep passing, though that
specific test's fixtures don't happen to use a detector-bearing
language, so it won't itself trip over this).

**Independent re-verification note**: this sub-phase's implementing
agent was interrupted mid-task by a monthly spend-limit cutoff and its
first stop notification came back with no structured report, just a
warning to treat its work as unverified. Rather than discard or re-do
the work, every claim in this section was independently re-checked by
reading the actual diffs and re-running real checks against a freshly
built `.so` (not trusted from the agent's own account) before being
trusted: per-owner identity for all four handle types plus cross-owner
non-sharing (reproduced directly in a throwaway script), the exact
`test_create_dynamic_ag` scenario end to end, the node tombstone's exact
documented coverage boundary (confirmed `name`/`type`/`model_asset`/
`extras`/`tags` read correctly post-removal while `full_name`/`to_dict`/
`children`/`parents`/`detectors` raise `LookupError`, exactly as
documented above), the `TooManyAssetsInField` Display fix, and the
newly-discovered pickling/detectors gap just above. All confirmed
accurate. The agent was later resumed (it had, in fact, continued past
its first stop and written the detailed sections above itself) and its
own report corroborates this independent pass.

**Next step:** ~~Phase 4b~~ - **done** - see "Phase 4b status" below.

### Phase 4b status (complete, independently verified)

The intermediate, interrupted status this section replaces is preserved
in git history for anyone who wants the blow-by-blow of the two
spend-limit interruptions; this section is the final, from-scratch
independently-verified writeup, matching every other completed phase's
rigor (every claim below was re-checked directly by the coordinator -
rebuilding the extension, running the full suite, reading the actual
diffs - not taken from an agent's self-report alone).

**Resumption sequence.** Picked up from the intermediate status with two
things to resolve first: the previously-reported `rustc` ICE, and a
baseline re-check. Neither held up: `cargo build --workspace`, a direct
`cargo build` in `python/maltoolbox-attackgraph-py`, and a full
`cargo build --release` from `python/maltoolbox-pyo3` (the
`extension-module` crate) all succeeded immediately - consistent with the
original suspicion of a corrupted incremental-compilation cache from the
concurrent/interrupted cargo invocations, not a real defect. Separately,
the `.so` previously copied into `maltoolbox/` turned out to be built
against the *system* Python (3.14) rather than the project's `.venv`
(3.13), causing `ImportError: undefined symbol: PyIter_NextItem` on
import - fixed by rebuilding via
`uv run maturin develop --release -m python/maltoolbox-pyo3/Cargo.toml`
(which correctly targets `.venv`'s Python) and copying
`.venv/lib/python3.13/site-packages/_native/_native.cpython-313-x86_64-linux-gnu.so`
over `maltoolbox/_native.cpython-313-x86_64-linux-gnu.so` - this manual
copy remains necessary after every rebuild until Phase 5 fixes the
`python-source` packaging wiring (maturin currently installs the
extension standalone at `site-packages/_native/` rather than nested
under the `maltoolbox` package). With a correct build, the baseline was
**15 failed, 84 passed, 3 deselected** (not the previously-reported 18 -
three failures, `test_wrong_labels` and the two `ExpressionsChain` tests
`test_interleaved_vars`/`test_attackstep_inherit`, were already fixed;
the `expr_chain.rs` wrapper the interrupted fork had started was in fact
complete and correctly wired in).

**Work was dispatched to implementing agents in three rounds** (the
first round ran three agents in parallel against disjoint file sets;
having seen that this still produces wasted work when the crates share
one compiled extension - see
[[feedback-serial-agents|the standing note on serial dispatch]] added to
memory this session - every subsequent round ran one agent at a time):

1. Root-caused all 15 failures directly (reading the actual Rust/Python
   source, not just pytest output) before dispatching anything, and
   recorded two new architecture decisions below (decisions 8 and 9).
   Dispatched three agents in parallel against disjoint files (Rust core
   determinism/`IndexMap`/`__deepcopy__`; `LanguageGraphAsset`/
   `AttackStep` pickling + `.detectors`; detached `AttackGraphNode` +
   live `.extras` + `AttackGraph(None)`). All three shared one compiled
   extension, so once two of them finished their own file-level work they
   had nothing left to do except poll a shared `cargo build` for the
   third's in-progress compile errors - wasted turns, stopped mid-poll
   both times (their already-written code was left in place, not
   reverted).
2. Rebuilt and re-ran the full suite directly: **94 passed, 5 failed, 3
   deselected**. Root-caused the remaining 5 directly before dispatching
   again (one agent only, this time, serially): no real `__deepcopy__`
   existed on `AttackGraph`/`AttackGraphNode` (relying on a generic
   pickle-based fallback that crashed); `test_attackgraph_according_to_corelang`
   had a second, deeper determinism bug beyond decision 7's original
   scope (`get_attacks_for_asset_type` in
   `crates/maltoolbox-language/src/graph/lookup.rs` was still a
   `HashMap`); `test_pickle_languagegraph_attack_step` silently resolved
   to the *wrong* step after a pickle round-trip (the temporary owner
   graph's deserialization path builds attack steps in a different
   global order than the normal build path, so a raw slotmap-id
   round-trip landed on a different entry in the reconstructed graph);
   `test_attackgraph_get_node_by_full_name` was by that point purely a
   fragile `repr(e)`/`tblen=` assertion (the actual message text already
   matched).
3. Rebuilt and re-ran the full suite directly: **99 passed, 3 deselected,
   0 failed**, confirmed stable across 3 consecutive runs. Then,
   independently (not agent-dispatched - small enough to do directly):
   found `ruff check .` was *not* actually clean (32 findings, all in
   shim files from this phase's cutover) - `PLC0414` (useless-import-alias)
   flagging the deliberate `from maltoolbox._native import X as X`
   re-export idiom the shim modules use throughout (needed so mypy treats
   these as intentional public re-exports), plus a couple of leftover
   unused imports in `test_partial_regeneration.py` and some unsorted
   import blocks. Added a `pyproject.toml` `[tool.ruff.lint] ignore =
   ["PLC0414"]` (this idiom is now a standing part of the shim-module
   pattern, not a one-off, so a blanket ignore beats enumerating every
   shim file and forgetting future ones) and ran `ruff check . --fix` for
   the rest.

**Final verification (independently re-run end to end, not relying on
any single agent's self-report):**
- `uv run pytest tests -m "not integration" -q` -> **99 passed, 3
  deselected, 0 failed** (99 = 107 original minus the 8
  `test_partial_regeneration.py` deletions from Phase 4 decision 2).
- `uv run ruff check .` -> all checks passed.
- `uv run mypy maltoolbox tests --ignore-missing-imports` -> no issues
  found in 46 source files.
- `uv run maltoolbox compile <lang>.mal <out>.mar` and
  `uv run maltoolbox generate-attack-graph <model>.yml <lang>.mar` both
  exit cleanly against real testdata fixtures.
- Not independently re-run this pass (no code in these areas changed
  since Phase 3, low risk, noted for completeness rather than re-verified
  from scratch): `visualization/`, `translators/` beyond what the pytest
  suite already exercises, `ingestors/`, neo4j/graphviz/draw.io backends.

**Former loose end, now fixed:** this section previously documented
`crates/maltoolbox-attackgraph/tests/test_partial_regeneration.rs` as a
known, accepted, not-CI-blocking gap - it called
`partially_generate::nodes_to_be_removed` with a `&HashMap` where the
signature now expects `&IndexMap` (a call site decision 7's `HashMap`->
`IndexMap` widening missed), failing `cargo clippy --workspace
--all-targets` and, as the user hit directly, plain `cargo test
--workspace` too (this repo's CI only runs `ruff`/`mypy`/`pytest`, so it
never surfaced there - but it does block local Rust-side testing).
Fixed: the one broken call site (`nodes_to_be_removed_missing_node_raises`,
passing `&HashMap::new()` for the `full_name_to_node` parameter) now
passes `&IndexMap::new()` instead, with a new `use indexmap::IndexMap;`
import added (the crate already depends on `indexmap` as a regular,
non-dev dependency, so no `Cargo.toml` change was needed - integration
tests get the same `[dependencies]` as the lib). The `removed_assets`
parameter on both `nodes_to_be_removed` and `partially_regenerate_graph`
is unaffected and correctly still `&HashMap<i64, AssetSnapshot>` - decision
7's widening was specifically for node/lookup maps needing deterministic
iteration order, not every map in the crate, so this was a true one-line
fix, not a wider pattern to hunt for. Verified: `cargo test --workspace`
(all crates, all 9 tests in this file including the previously-broken
one) passes clean.

`cargo clippy --workspace --all-targets` still had one pre-existing,
unrelated warning at this point (`clippy::redundant_guards` on
`Some(id) if id.is_empty()` in `crates/maltoolbox-language/src/compiler/
semantic.rs:143`, predating this whole phase, nothing to do with the
`HashMap`/`IndexMap` fix) - also fixed, applying clippy's own suggested
rewrite verbatim (`Some(id) if id.is_empty()` -> `Some("")`). `cargo
clippy --workspace --all-targets` is now genuinely zero-warning, not just
zero-error.

**`tests/translators/test_updater.py`'s change, now confirmed** (flagged
as unexplained in the intermediate status): the diff adds a
`_to_dict_ignoring_version` test helper with a docstring that already
explains it fully - two of the old-schema fixtures
(`simple_example_model_0.0.38.json`/`simple_example_model_0.1.8.yml`)
predate the `"MAL-Toolbox Version"` metadata field entirely, so
`load_model_from_older_version` fills in the live `maltoolbox.__version__`
as a default, which can never equal the comparison fixture's own
explicitly-recorded version. This only ever passed before because of a
separate, since-fixed pure-Python bug where `to_dict()` ignored
`self.maltoolbox_version` and always wrote the live version on *both*
sides regardless (Phase 2 status below, "...ignoring
`self.maltoolbox_version` entirely..." - an intentional, accepted
divergence per `PORTING_NOTES.md` §3). Confirmed genuinely explained, not
a loose end.

### Phase 5 status: packaging (done)

Covers the three items listed under "Packaging (Phase 5, not started)"
above, in order.

**`[build-system]` moved to `maturin`.** Root `pyproject.toml`'s
`[build-system]` now reads `requires = ["maturin>=1,<2"]` /
`build-backend = "maturin"`, replacing `setuptools`. The `[project]`
metadata table (name/version/authors/dependencies/scripts/etc.) is
untouched - maturin reads standard PEP 621 metadata directly, so none of
that needed to change. `[tool.setuptools.packages.find]` and
`[tool.setuptools.package-data]` are gone, replaced by a new
`[tool.maturin]` table:
```toml
[tool.maturin]
manifest-path = "python/maltoolbox-pyo3/Cargo.toml"
module-name = "maltoolbox._native"
python-source = "."
include = ["maltoolbox/py.typed", "maltoolbox/*.conf*"]
```
`manifest-path` points at the existing umbrella extension crate (its
`[workspace]`/path-dependency wiring into `python/maltoolbox-{language,
model,attackgraph}-py` and `crates/*` is unchanged - still a separate
Cargo workspace from the root one, as before). `include` replaces the old
`package-data` entry for the two non-`.py` files the package ships
(`py.typed`, `*.conf*`).

**`python-source` wiring fixed - this was the actual blocking problem.**
Setting `python-source = "."` (repo root, same directory as
`pyproject.toml`, which already contains the real `maltoolbox/` package)
was the whole fix. Verified directly, not assumed: deleted the manually-
copied `maltoolbox/_native.cpython-313-*.so` first, then ran a plain
`uv sync` from a clean state - maturin's PEP 660 editable-install hook
built the extension and placed `maltoolbox/_native.cpython-313-x86_64-
linux-gnu.so` directly inside the real `maltoolbox/` package in the repo
(not a separate `site-packages/_native/`), and `import maltoolbox._native`
resolved correctly with zero manual steps. The old manual-copy workaround
(`uv run maturin develop --release -m python/maltoolbox-pyo3/Cargo.toml
&& cp .venv/.../_native*.so maltoolbox/...`) documented throughout this
plan is now obsolete - plain `uv sync` (or any `uv run <cmd>`, which
triggers a rebuild check automatically) is sufficient after a Rust
change. `uv run <cmd>` with no Rust changes pending stays fast (~30ms
overhead, confirmed by timing) - the rebuild check is cheap when nothing
changed.

**`cibuildwheel` CI config added (superseded below - kept for history).**
Originally folded a `cibuildwheel`-based `build-wheels` job into the
existing `.github/workflows/publish-to-pypi-and-test-pypi.yml`: ran
`pypa/cibuildwheel@v4.2.1` across `ubuntu-latest`/`macos-latest`/
`windows-latest` (CPython 3.10-3.14, skipping musllinux/manylinux i686 and
win32), with `CIBW_BEFORE_ALL_LINUX` installing a Rust toolchain into the
manylinux/musllinux containers once per container (not
`CIBW_BEFORE_BUILD_LINUX`, which would reinstall it once per CPython
target built inside that same container), plus `CIBW_TEST_COMMAND:
'python -c "import maltoolbox"'`; a separate `build-sdist` job ran
`maturin sdist`. This version came from a second pass after an external
review of the first cut of this workflow caught several things worth
fixing - see git history around this point for the review content if
useful context is ever needed. The `publish-to-pypi`-needs-
`publish-to-testpypi` sequencing (TestPyPI as a real gate, not a
simultaneous no-ordering publish) and the tag-gated `if:` conditions
introduced in this pass carried forward unchanged into the
`maturin-action` rewrite below.

**Superseding rewrite: switched the build jobs from `cibuildwheel` to
`PyO3/maturin-action@v1`**, per explicit user request to use the
Rust-ecosystem-native tool and follow current best practices for a
PyO3/maturin project specifically (not just "any compiled-extension
package" best practices, which is what the `cibuildwheel` pass was
following). Source of truth: ran `maturin generate-ci github` locally
(maturin 1.15.0) rather than trusting secondhand summaries of
`maturin-action`'s README, since an earlier fetch of that README had
already produced one visibly-hallucinated detail (a QEMU `if:` condition
comparing a matrix field to itself). The generator's live output revealed
`maturin-action` needs no manual Rust-toolchain bootstrapping at all
(unlike `cibuildwheel`, which needed the `CIBW_BEFORE_ALL_LINUX` rustup
curl-install) - it runs inside manylinux/musllinux containers that already
carry a Rust toolchain, and handles aarch64 cross-compilation internally
with no explicit QEMU setup step in the generated output, so none was
added here either.

**A critical bug found and fixed before wiring this up, not merely a
style choice:** the generator, when pointed at the extension crate's
manifest via `-m python/maltoolbox-pyo3/Cargo.toml`, emits `args:
--manifest-path python/maltoolbox-pyo3/Cargo.toml` in every build step.
Tested by hand: `maturin build --manifest-path python/maltoolbox-pyo3/
Cargo.toml` run from the repo root does **not** use the repo-root
`pyproject.toml`'s `[tool.maturin]` config - it resolves pyproject.toml
configuration from the directory containing that `Cargo.toml` instead,
which found the stale `python/maltoolbox-pyo3/pyproject.toml` (its
`module-name` set, but no `python-source` override) and silently built a
wholly wrong wheel: `maltoolbox_native-0.1.0-...whl`, not
`mal_toolbox-2.11.0-...whl`, with none of the real package's files in it.
Deleting that nested file and re-running produced an equally-wrong result
from a different cause - no pyproject.toml found at all, so maturin fell
back to the Cargo package's own `[package] name = "maltoolbox-pyo3"` for
metadata, still ignoring the real package. The fix, confirmed working:
regenerate with no `-m` flag at all, which resolves `manifest-path` from
the repo-root `pyproject.toml`'s own `[tool.maturin]` table (already set
there - see "Packaging" above) - `args` in the final workflow has no
`--manifest-path` anywhere. Verified directly: `maturin build --release`
with no flags, run from repo root, produces
`mal_toolbox-2.11.0-cp313-cp313-manylinux_2_34_x86_64.whl` with
`maltoolbox/_native.cpython-313-...so` correctly nested inside, matching
local `uv sync` behavior exactly. The now-proven-dangerous
`python/maltoolbox-pyo3/pyproject.toml` was deleted outright (see the
correction note above, in the original Phase 5 writeup, where it had
been wrongly called "harmless").

**Final job structure:** `linux` (manylinux, `x86_64`+`aarch64`, one job
per target via a matrix, `manylinux: auto`), `musllinux` (same two
targets, `manylinux: musllinux_1_2`), `windows` (`x64` only), `macos`
(`x86_64` on `macos-15-intel` + `aarch64` on `macos-latest`, both native -
not cross-compiled, since GitHub's `macos-latest` runner is Apple Silicon
and `macos-15-intel` is the explicit Intel runner), `sdist`. **Deliberately
scoped down from the generator's full default matrix**, which also
includes `x86` (32-bit), `s390x`, `ppc64le`, `armv7`, and Windows `x86`/
`arm64` - dropped as very unlikely to have real demand for this package;
trivial to add back from the generator's raw output
(`/tmp/.../generated-ci-v2.yml`-equivalent, regenerate with `maturin
generate-ci github` if needed) if that changes. Each build job sets
`sccache: ${{ !startsWith(github.ref, 'refs/tags/') }}` (cache for regular
CI runs, but force a clean uncached build for actual release artifacts -
taken directly from the generator's own default, not invented here) and
`--find-interpreter` (maturin auto-discovers whatever CPython
interpreters are present on the runner/in the container rather than a
hardcoded version list - simpler than `cibuildwheel`'s explicit
`CIBW_BUILD` list, but means Python-version coverage for Windows/macOS
wheels depends on what `actions/setup-python`/the runner image actually
provides rather than an explicit choice; not yet confirmed against a real
CI run which versions this actually produces). A `Test wheel` step
(`pip install` the built wheel + `python -c "import maltoolbox"`) was
added on every native-arch build (`linux`/`musllinux` only on their
`x86_64` matrix entry, both `macos` entries, the single `windows` entry) -
`maturin-action` has no built-in equivalent to `cibuildwheel`'s
`CIBW_TEST_COMMAND`, so this is hand-rolled; skipped for the cross-compiled
`aarch64` Linux entries since there's no QEMU/emulation set up to actually
execute a foreign-arch binary on an `x86_64` runner.

**Publish jobs unchanged in mechanism, renamed `needs` targets only:**
still `pypa/gh-action-pypi-publish@release/v1` via OIDC trusted publishing
(not the generator's own default of `uv publish` + a stored
`PYPI_API_TOKEN` secret - deliberately kept, since trusted publishing/no
stored secret is the better-established practice and was already reviewed
and committed to earlier in this phase), still `publish-to-testpypi`
before `publish-to-pypi` with the latter `needs`-ing the former, still
tag-gated via the same `if:` conditions, still `on: push` at the top level
(unchanged, per the explicit instruction not to touch the trigger).
Artifact naming switched to the generator's `wheels-<platform>-<target>`
convention (was `python-package-distributions-<os>`) since a target-level
matrix within one job - new with `maturin-action` - needs unique names per
matrix entry, not just per job.

**One new hardening item added beyond what was already there, taken
directly from the generator's default:** a GitHub-native build-provenance
attestation step (`actions/attest@v4`, requiring a new `attestations:
write` permission) added to `publish-to-pypi` only, over the final
`dist/*` artifacts right before the real PyPI publish. This is separate
from and additional to the Sigstore/PEP 740 attestations
`gh-action-pypi-publish` already generates automatically for trusted-
published packages (uploaded to PyPI itself) - this one is GitHub-native,
independently verifiable via `gh attestation verify` without going through
PyPI at all. Not added to `publish-to-testpypi`, since attesting test-only
artifacts adds no real value.

Standard GitHub Actions versions bumped to match the generator's current
defaults rather than the versions this workflow happened to already be
on: `actions/checkout@v4`->`v6`, `actions/setup-python@v5`->`v6`,
`actions/upload-artifact@v4`->`v6`, `actions/download-artifact@v4`->`v7`.

**Trigger kept identical to `main` (`on: push`), per explicit user
instruction** ("this branch is not for updating/modifying CI, just for
porting to the Rust backend"). An earlier pass on this branch narrowed the
trigger to `push: tags: [...]` (reasoning: `cibuildwheel` now compiles the
Rust extension across a multi-platform matrix on every build, materially
more expensive than the old pure-Python `pip install build` the same
trigger used to run) - correctly caught as out-of-scope CI-policy
tinkering and reverted. Net effect, carried forward unmodified from
`main`: `build-wheels`/`build-sdist` still run on every push (now
compiling Rust instead of pure Python - an unavoidable consequence of the
backend port itself, not a policy change made on this branch); only the
`publish-to-pypi`/`publish-to-testpypi` jobs are tag-gated, via their
existing `if: startsWith(github.ref, 'refs/tags/')` conditions (also
unmodified from `main`). Separately worth noting: `main`'s tags are plain
semver (`2.11.0`, `0.0.10`, ...), never `v`-prefixed - confirmed via `git
tag -l`, all 88 existing tags match `^[0-9]+\.[0-9]+\.[0-9]+$` - so had a
tag-based trigger been kept, the pattern would have needed to be
`[0-9]+.[0-9]+.[0-9]+`, not `v*`. Not applicable now that the trigger
matches `main`, but worth remembering if a tag-gated trigger is ever
revisited outside this branch's scope.

This has not been exercised by an actual tag push or GitHub-hosted CI run
yet - the YAML was validated for syntax (`yaml.safe_load`), the exact
`maturin build` invocation the workflow uses was verified by hand locally
(see above - this is what caught the `--manifest-path` bug), but the
`maturin-action`-in-CI path specifically (container selection, aarch64
cross-compilation, `--find-interpreter`'s actual Python-version coverage
on the GitHub-hosted Windows/macOS runners) is still unverified against
real CI and should be smoke-tested before the first real release tag.

**README updated** with a `### Requirements` note that building from the
sdist (i.e. no prebuilt wheel matches the installer's platform/Python
version) now requires a Rust toolchain, linking rustup.rs.

**Full verification bar, re-run after the `pyproject.toml` switch:**
`uv run pytest tests -m "not integration" -q` -> 99 passed, 3 deselected
(unchanged from Phase 4b); `uv run ruff check .` -> all checks passed;
`uv run mypy maltoolbox tests --ignore-missing-imports` -> no issues in
46 source files; CLI spot checks (`uv run maltoolbox compile`/
`generate-attack-graph` against real testdata fixtures) exit cleanly and
raise correctly-mapped exceptions (`MalSyntaxError`, `ModelException`) on
bad input, round-tripping through the now-maturin-built extension exactly
as before the packaging change.

**Correction to this section's original claim, found and fixed in the
`maturin-action` CI pass below:** the nested
`python/maltoolbox-pyo3/pyproject.toml` was originally left in place here
as "harmless." It is not. Confirmed by hand: `maturin build --manifest-path
python/maltoolbox-pyo3/Cargo.toml` (the exact invocation style
`maturin-action`/`maturin generate-ci` produce when given an explicit
manifest path) resolves pyproject.toml configuration from the directory
*containing that Cargo.toml*, not the repo root - so it silently picked up
the stale nested file's `module-name`/missing `python-source` and built a
wheel named `maltoolbox_native-0.1.0` with the wrong internal layout,
ignoring the real `mal-toolbox` package entirely, no error or warning.
Deleted in the Phase 5 CI follow-up (see below) once this was confirmed;
the fix is to never pass `--manifest-path` to `maturin`/`maturin-action` at
all and let it resolve everything from the root `pyproject.toml`'s own
`[tool.maturin] manifest-path` setting instead (verified: `maturin build`
with no `--manifest-path` run from repo root correctly produces
`mal_toolbox-2.11.0...whl` with `maltoolbox/_native...so` nested
correctly).

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

### Phase 3 status: `AttackGraph`/`AttackGraphNode`/`Detector` (complete, several logged gaps)

New `python/maltoolbox-attackgraph-py` crate (1,375 lines across 7
files; depends on `maltoolbox-attackgraph`/`maltoolbox-model`/
`maltoolbox-language` (core) and `maltoolbox-language-py`/
`maltoolbox-model-py` (per the established cross-layer dependency
pattern) - required `maltoolbox-model-py`'s `mod asset`/`mod exceptions`
to become `pub mod` (same zero-behavior-change visibility-only pattern
as Phase 2's `maltoolbox-language-py` change) so `Tombstones`/
`model_error_to_py`/`PyModelAsset`'s fields are reachable):

- `graph.rs` - `PyAttackGraph`: the container, `Rc<RefCell<
  maltoolbox_attackgraph::AttackGraph>>` plus `lang_graph_py: Py<
  PyLanguageGraph>` and `model_py: Option<Py<PyModel>>` (both the actual
  Python objects passed in, identity-preserving - `.lang_graph`/`.model`
  confirmed via `is` to return the same object every time, same pattern
  as Phase 2 decision 4). Constructor matches Python exactly:
  `AttackGraph(lang_graph, model=None)`. When `model` is given, reuses
  `model.inner.borrow().lang_graph.clone()` (an `Rc` clone, no data copy)
  rather than re-cloning `lang_graph_py`'s data - cheaper than `PyModel`'s
  own constructor has to be, since here there's already a model in hand
  with its own bare `Rc<LanguageGraph>` to borrow from. Full parity:
  `lang_graph`/`model` (getter+setter, matching Python's plain mutable
  `self.model` attribute - changing it doesn't retroactively change
  already-built node handles' owner, which is correct, matching Python
  since nodes don't hold `model` themselves either)/`next_node_id`/
  `nodes` (Phase 3 decision 2's lazy view, see `node.rs`)/
  `full_name_to_node`/`attack_steps`/`defense_steps` (plain rebuilt-fresh
  dict/list, Phase 1/2's pattern - lower usage, not hot-path)/`detectors`
  (Phase 3 decision 1's lazy live list, see below) getters,
  `get_node_by_full_name`/`regenerate_graph`/`partially_regenerate_graph`/
  `add_node`/`remove_node`/`to_dict`/`_to_dict`/`save_to_file`/
  `load_from_file` (`#[staticmethod]`)/`__repr__`/`__reduce__`/
  `_from_pickle_state` (`#[staticmethod]`) methods. `create_attack_graph`
  lives in `factories.rs` instead (a module-level function in Python
  too, not a method).
- `node.rs` - `PyAttackGraphNode`: a handle - **per Phase 3 decision 3,
  holds `owner_py: Py<PyAttackGraph>`, not a bare `Rc<RefCell<
  AttackGraph>>`** - resolves the core's `AttackGraphNodeId` slotmap key
  from the stable Python-facing `i64` id on every access (no cache, same
  discipline as `PyModelAsset`). Mechanical consequence of this design
  choice, confirmed while implementing: `Py<T>` is *not* plain `Clone`
  in this pyo3 version (0.29.3) - it only has `clone_ref(py)`, which
  needs a GIL token - so unlike every earlier handle type in this
  project (which held a bare `Rc<RefCell<_>>`, always `Clone`),
  `PyAttackGraphNode`/`PyDetector` can't `#[derive(Clone)]` and instead
  get a manual `clone_ref(&self, py) -> Self` method; every call site
  that used to just `.clone()` a handle (building a `set`/`dict` of
  them, storing one in a `Detector`, etc.) was updated to thread `py`
  through and call `.clone_ref(py)` instead - caught immediately by the
  compiler (`Py<PyAttackGraph>: Clone` not satisfied), not a silent gap.
  Full parity: `id`/`name`/`type` (`#[getter(r#type)]`)/`lg_attack_step`
  (builds a `PyLanguageGraphAttackStep` via `owner.lang_graph_py`)/
  `causal_mode`/`ttc`/`tags`/`model_asset` (builds a `PyModelAsset` via
  `owner.model_py` - `None` if either is absent)/`existence_status`/
  `children`/`parents` (sets of handles)/`extras`/`detectors` (Phase 3
  decision 1, see below)/`full_name`/`info`/`additive_model_effects`/
  `subtractive_model_effects` (see Open gaps) getters, `to_dict`/
  `__repr__`/`__hash__`/`__richcmp__`/`__reduce__` methods. Also hosts
  `PyAttackGraphNodesView` (Phase 3 decision 2's lazy, read-only
  Mapping-protocol wrapper for `.nodes` - `__getitem__`/`__len__`/
  `__contains__`/`__iter__`/`keys`/`values`/`items`/`get`, each
  constructing a `PyAttackGraphNode` handle only for key(s) actually
  touched; not `m.add_class`'d, not part of the public surface, only
  ever handed out by `PyAttackGraph.nodes`) and the module-level
  `_rebuild_attack_graph_node(owner, id)` pyfunction `__reduce__`
  delegates to.
- `detector.rs` - `PyDetector`: unlike every other type in this layer, a
  real freely-constructible value (`#[new]`) - confirmed unproblematic
  (not a Phase 1/2-style freeform-construction hazard) since it only
  ever wraps a reference to an *existing* node handle, never needs
  detached construction; confirmed necessary at all because
  mal-simulator imports and constructs `Detector` directly
  (`test_logger_attacks_false_negative`/`_false_positive`). Fields:
  `name`/`node: PyAttackGraphNode`/`potential_context: Py<PyDict>`/
  `tprate`/`fprate`. `__hash__` always raises `TypeError` (mirrors the
  real runtime effect of Python's frozen-dataclass auto-`__hash__` here,
  which would also raise at `hash()` time since `potential_context` is
  an unhashable `dict` - not a divergence, a different mechanism
  producing the same outcome). `to_dict` matches the core's own
  simplified detector serialization (`name`/`tprate` only), not
  Python's actually-broken `Detector.to_dict()` (confirmed broken by
  testing - see Open gaps). `__reduce__` added after initially omitting
  it: confirmed by direct testing that without it, `pickle.dumps(a_
  detector)` raises `TypeError: cannot pickle` (pyo3's default protocol
  needs `cls.__new__(cls)` with no args, but `#[new]` here requires
  `node`/`potential_context`) - fixed by using `PyDetector`'s own class
  as the `__reduce__` target directly (unlike the container types, it
  *is* directly callable with exactly the right positional args, so no
  separate `_from_pickle_state` indirection needed).
- `detector_support.rs` - shared plumbing for Phase 3 decision 1:
  `DetectorSnapshot` (owned, borrow-free: label, node id, name,
  `potential_context: HashMap<String, Vec<i64>>`, tprate, fprate) and
  `detector_snapshots_for(graph, keys)`/`build_py_detector(py, owner_py,
  snapshot)`, used by both `graph.rs`'s flat-list seeding and `node.rs`'s
  per-node-dict seeding so the "snapshot everything needed with no
  outstanding core-graph borrow, then build Python objects" discipline
  lives in one place.
- `exceptions.rs` - `AttackGraphException(MalToolboxException)` +
  `AttackGraphStepExpressionError`, same crate-dependency-reuse pattern
  as `ModelException`. `graph_error_to_py` (context-free default
  mapping: `DuplicateNodeId` -> `ValueError` matching `AttackGraph
  .add_node`'s real `raise ValueError(...)`; `StepExpression` ->
  `AttackGraphStepExpressionError`; `Malformed` -> the base
  `AttackGraphException`; `Language`/`Model` delegate to the respective
  layer's own mapper) plus `graph_error_to_lookup` (for call sites that
  know, from reading the real Python source, that *any* failure there is
  a `LookupError` - `get_node_by_full_name`, `from_dict`'s "Failed to
  find ..." messages - since the core's `Malformed` variant is an
  overloaded catch-all covering several distinct Python exception types,
  not just one).
- `factories.rs` - `create_attack_graph(lang, model)`: a module-level
  function (registered directly on `_native`, not a method), matching
  Python's real signature exactly (`lang`/`model` each accept either a
  path string or an already-loaded object) - deliberately *not* reusing
  the Rust core's own `maltoolbox_attackgraph::factories::create_attack_graph`
  (path-only, returns `(AttackGraph, Model)` tuple since the core
  doesn't store `model` on `AttackGraph`); this binding's version builds
  the `PyLanguageGraph`/`PyModel` objects itself when given paths and
  constructs a `PyAttackGraph` with the compat layer's own `.model`
  back-reference, matching Python's actual return shape (just the
  `AttackGraph`, with `.model`/`.lang_graph` already set).
- **Two small opportunistic core-crate changes, flagged**: (1)
  `crates/maltoolbox-attackgraph/src/graph.rs`'s `node_to_dict` made
  `pub` (was private) so `AttackGraphNode.to_dict` in this layer can
  reuse the exact same single-node serialization the graph's own
  `to_dict` uses for each node - zero behavior change, visibility only.
  (2) `PyLanguageGraph`/`PyModel` (Phase 1/2, already-committed files)
  each gained `module = "maltoolbox._native"` on their `#[pyclass]`
  attribute (previously unset, defaulting to pyo3's own fallback) and a
  `__reduce__`/`_from_pickle_state` pair, closing out the pickling work
  Phase 1/2 deferred to this phase (Phase 2 decision 3) - `PyAttackGraph`
  needed both of its nested layers to be genuinely picklable first,
  since its own pickled state bundles theirs.
- Registered in `python/maltoolbox-pyo3` (`Cargo.toml` dependency +
  `maltoolbox_attackgraph_py::register(py, m)?` call), same pattern as
  Phases 1-2.

**Phase 3 decision 1 (live detectors) implementation shape, as built:**
`PyAttackGraph` holds `detectors_list: Rc<RefCell<Option<Py<PyList>>>>`
(`None` until first `.detectors` access) and `node_detectors: Rc<RefCell<
HashMap<i64, Py<PyDict>>>>` (populated lazily per node id). Both are
seeded from `DetectorSnapshot`s read from the core's per-node `detectors:
HashMap<String, Detector>` at the moment of first access, then never
consulted again - confirmed this handles both orderings correctly
(whether `.detectors` is first read before or after a
`partially_regenerate_graph` call) since a first-ever access always
seeds from *whatever the current full state is*, and a later access
after the list already exists only appends the newly-created nodes'
detectors (matching Python's `self.detectors.extend(new_detectors)`
exactly - existing entries, including any external mutation of them,
are left untouched). `regenerate_graph` resets both containers entirely
(matches Python discarding every old node on a full rebuild).
`remove_node` purges the removed id's `node_detectors` entry;
`partially_regenerate_graph` additionally diffs node-id-sets
before/after the core call to purge entries for any node removed as a
*side effect* internally (the core's own `removal_candidates` handling,
not directly surfaced back to this binding) - without this, a removed
node's stale per-node detector dict would linger indefinitely.

**Phase 3 decision 2 (lazy `.nodes` view) implementation note:**
`PyAttackGraph.nodes`/`.detectors`/`.full_name_to_node`/`.attack_steps`/
`.defense_steps` all needed a `Py<Self>` to hand out (to build node
handles owned by *this* graph), which a method can't get from a plain
`&self` receiver - pyo3 supports this via taking `self_: &Bound<'_,
Self>` as the receiver instead and calling `self_.clone().unbind()`;
used throughout this file rather than restructuring construction to
pass `Py<Self>` down some other way.

**Verified** (matching Phases 1-2's rigor):
- `cargo build`/`cargo clippy --all-targets` clean on the new crate and
  the `maltoolbox-pyo3` umbrella - zero warnings (three
  `clippy::type_complexity` warnings on `__reduce__`-shaped tuple return
  types fixed with `#[allow(clippy::type_complexity)]`, matching the
  existing `#[allow(clippy::too_many_arguments)]` precedent for
  pyo3-driven unavoidable complexity).
- `cargo build --workspace`/`cargo test --workspace`: still exactly 117
  tests passing (confirms `python/` crates, including the new one,
  remain correctly isolated from the root workspace).
- `maturin develop` (release profile) builds/installs cleanly; same
  known wrong-install-location workaround as every prior phase.
- **Oracle diff against the real pure-Python implementation**, with one
  methodology refinement specific to attack graphs (see the first
  "Newly confirmed, logged, pre-existing finding" below): built an
  equivalent model (3 assets, 2 associations) through both
  `_native.AttackGraph`/`AttackGraphNode` and the untouched
  `maltoolbox.attackgraph.AttackGraph` in the same process, compared
  `_to_dict()` **structurally** (by `full_name`, not raw numeric node
  id) - exact match. Repeated after `partially_regenerate_graph` (add an
  asset, then remove one) and after `regenerate_graph` - exact
  structural match every time. `save_to_file`/`load_from_file`
  round-trip compared by **exact** `_to_dict()` (ids *do* round-trip
  exactly here, since `from_dict` reads them verbatim rather than
  reassigning - confirmed, see the finding below for why this differs
  from fresh generation).
- Dict/set keying: fetched the same node two different ways
  (`get_node_by_full_name` and `.nodes[id]`), confirmed `==`/`__hash__`
  match and set-collapse - same check style as Phases 1-2.
- **Confirmed-necessary mal-simulator patterns, reproduced directly**
  (not just reasoned about), using the real `tests/testdata/
  detector_lang.mal` fixture (the same one mal-simulator's own
  `detector_lang_scenario.yml` test uses): built a graph with a real
  language-level detector, then - `node.detectors['logExploit'] =
  Detector(...)` followed by a *second, independent* `.detectors`
  access on the same node confirmed the mutation persisted;
  `attack_graph.detectors.remove(old)`/`.append(mocked)` followed by a
  second independent `.detectors` access confirmed the same; confirmed
  the per-node dict and flat list stayed independently mutable
  (mutating one didn't affect the other) - matching the real,
  confirmed-by-reading-Python-source redundant/unsynchronized behavior
  from Phase 3 decision 1.
- `.nodes` lazy mapping: `__getitem__`/`__len__`/`__contains__`/`in`/
  `.values()`/`.keys()`/`.items()` all checked against a real generated
  graph and matched the oracle's plain `dict` for every access pattern.
- **Pickling** (Phase 3 decision 4), a real conformance test mirroring
  `test_simulator_picklable` exactly: `LanguageGraph`/`Model`/
  `AttackGraph` each pickle/unpickle with an exact `_to_dict()`/
  `to_dict()` match; a single bare `AttackGraphNode` pickles/unpickles
  standalone without crashing; pickling `(attack_graph, node)` together
  in *one* `pickle.dumps` call and unpickling confirmed the restored
  node's owner is the *same* restored graph object (`is`, not just
  `==`) - the identity-sharing-via-pickle-memoization design worked
  exactly as the decision predicted, verified directly, not assumed. A
  bare `Detector` also pickles/unpickles correctly (data-wise) standalone
  and shares owner identity when combined with its graph in one call,
  same as a node.
- Error mapping spot-checked against real conditions: `get_node_by_full_name`
  miss -> `LookupError`; `add_node` duplicate id -> `ValueError`;
  `create_attack_graph` with a bad `lang` type -> `TypeError`.
- `create_attack_graph` verified both call shapes (`(path, path)` and
  `(LanguageGraph, Model)`), confirming `.lang_graph is`/`.model is`
  identity for the object-argument case.
- Full existing pytest suite unaffected - **no `.py` file was touched by
  this phase** (confirmed via `git status`): `uv run pytest tests -m
  "not integration"` - 107 passed, 3 deselected, identical to every
  prior baseline. `uv run ruff check .` - clean (trivially, since
  nothing Python changed).

**Newly confirmed, logged findings (pre-existing, not introduced by this
phase, not blocking):**
1. **Fresh `generate_graph` node-id *numbering* isn't guaranteed to
   match Python's, even for an isomorphic graph** - confirmed by running
   the oracle diff and finding every node's numeric `id` differed
   (structurally, everything else was identical) between a freshly
   generated native graph and the Python oracle for the same model.
   Root cause, confirmed by reading the (pre-existing, not touched by
   this phase) core crate: `crates/maltoolbox-attackgraph/src/
   generate.rs`'s `create_nodes_for` assigns sequential ids while
   iterating each asset's attack steps via `LanguageGraphAsset
   .attack_steps: HashMap<String, AttackStepId>` - a `HashMap`, not an
   insertion-ordered structure - so the exact id a given step lands on
   depends on Rust's (per-process-randomized-by-default) hash iteration
   order, not the declaration order Python's own dict-based equivalent
   preserves. This has no observable effect on correctness (every
   consumer resolves nodes by `full_name`/id-returned-from-the-same-call,
   never by assuming a specific number in advance) and doesn't affect
   `from_dict`/`load_from_file` (those read ids verbatim from the
   serialized form, this issue is specific to *fresh* generation) - but
   it does mean an oracle diff comparing fresh-generation `_to_dict()`
   output byte-for-byte will never match on the numeric ids, only
   structurally. Not fixed here (would mean changing already-tested core
   generation-order semantics, well outside this phase's scope) - logged
   for whoever next touches `generate.rs`, if reproducible byte-for-byte
   generation output is ever needed.
2. **The pure-Python oracle's own `Detector.to_dict()`/`AttackGraph
   ._to_dict()` crash outright on any detector-bearing graph** -
   confirmed by direct testing (not just reading `PORTING_NOTES.md`'s
   note about it): `json.dumps(ag_python._to_dict())` raises `TypeError:
   Object of type AttackGraphNode is not JSON serializable`, since
   `Detector.to_dict()` embeds the live `node`/`potential_context`
   object references unconditionally. This port's `node_to_dict`/
   `PyDetector.to_dict` use the already-fixed simplified serialization
   (name/tprate only), so the *native* side has no such bug - but it
   means no oracle diff can ever be done against the Python original for
   a detector-bearing graph's full `_to_dict()`; the detector-specific
   verification above compares native-against-itself plus direct
   attribute access against the oracle instead.

**Open gaps, logged not silently skipped:**
1. **`AttackGraphNode` has no post-removal-readability tombstone** - the
   `AttackGraphNode` analog of Phase 2's `AssetSnapshot` gap, left
   unresolved this phase. A node handle resolves by looking up its id in
   `owner.inner.borrow().id_to_node` on every access; once `remove_node`
   (or a `partially_regenerate_graph`-internal removal) deletes that
   entry, the handle can no longer resolve itself - any getter raises
   `LookupError`, whereas a real Python `AttackGraphNode` object stays
   fully readable after removal (same shape of gap, same root cause:
   handle-by-id vs. live-object-reference). **Not currently known to be
   load-bearing** - grepped `tests/attackgraph/test_attackgraph.py
   ::test_attackgraph_remove_node` (the one existing test that calls
   `remove_node`): it only does `not in`/membership checks on the
   removed node afterward (needs `__hash__`/`__richcmp__`, which don't
   need to resolve the node's data), never reads an attribute of the
   removed node itself - so this gap has no reproducing test today,
   unlike Phase 2's analogous gap which did. Flagged anyway, since
   Phase 4's cutover could surface a case this misses, and the fix shape
   would mirror `AssetSnapshot` closely if ever needed (a per-node-id
   tombstone map on `PyAttackGraph`, populated by `remove_node`/the
   `partially_regenerate_graph` removal path).
2. **`additive_model_effects`/`subtractive_model_effects` raise
   `NotImplementedError` when non-empty** (the common `None`/empty case
   is fully correct). Deepened from Phase 1 gap #3's "nothing uses it"
   finding: `tests/attackgraph/test_attackgraph.py::test_create_dynamic_ag`
   *does* exercise this directly (DynaMAL model effects, deep structural
   access: `.base[i].field_name`, `.targets[i].assoc_traversal[j]
   .asset_filter.name`, etc.) - but only against the still-intact
   pure-Python oracle, not through the native bindings, so this doesn't
   block Phase 3 today. Confirmed via a fresh mal-simulator grep that
   nothing in its acceptance surface touches this. Faithfully exposing
   it needs a multi-class wrapper hierarchy over
   `LanguageGraphModelEffect`/`AssocTraversalChain`/`AssocTraversalElem`/
   `DynTarget` (each potentially resolving a `PyLanguageGraphAsset` via
   `asset_filter`) - a meaningfully sized sub-project of its own,
   deliberately not attempted under this phase's time budget. Will need
   to be resolved (built, or `test_create_dynamic_ag` explicitly
   adjusted) before Phase 4 can cut over `maltoolbox/attackgraph/node.py`
   without regressing that test.
3. **`AttackGraphNode.__deepcopy__` not implemented.** Grepped a fresh
   mal-simulator clone: zero `copy.deepcopy` usage anywhere. mal-toolbox's
   own `tests/attackgraph/test_attackgraph.py::test_attackgraph_deepcopy`/
   `test_deepcopy_memo_test` exercise it, but through heavy `id()`-based
   object-identity assertions (`id(copied_node) == id(same_node)` etc.)
   that are fundamentally incompatible with the owner+id handle design
   (freshly-constructed handles never share Python object identity) -
   same category as Phase 1/2's freeform-construction-style gaps, not
   attempted here, deliberately out of scope since nothing in the
   acceptance surface needs it. Will need an explicit decision at Phase
   4 (most likely: rewrite or drop these two tests, mirroring Phase 1's
   `dummy_lang_graph` resolution).
4. **`ExpressionsChain` still has no wrapper class** (Phase 1 gap #2,
   unchanged - not revisited this phase, since nothing in the
   `AttackGraph`/`AttackGraphNode` surface needed one; `tests/attackgraph/
   test_partial_regeneration.py`'s raw `ExpressionsChain(...)`
   construction remains the Phase 4 concern already logged in Phase 3
   decision 5).
5. **The `LoadError`/compiler-exception-mapping gap from Phase 1's
   Architecture section is still open** (unrelated to this phase,
   re-noted only because it's still the oldest open item in this
   document).

**Phase 3 is complete** - the open gaps above are logged, scoped,
confirmed non-blocking for the mal-simulator acceptance surface (the
goal this whole effort is ultimately judged against), and none
contradict "the existing `tests/` suite keeps passing" (nothing was cut
over yet, so nothing in `tests/` runs against the native bindings today
regardless).

**Next step:** see "Phase 4a status" near the top of this Status
section (right after `## Status`) for the full writeup - Phase 4a
(handle-cache retrofit, model-effects wrapper, node tombstone) is done;
Phase 4b (the actual file-level cutover) is next.
