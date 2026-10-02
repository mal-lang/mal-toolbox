# Porting notes: differences from mal-toolbox (Python) and remaining work

This document tracks how this Rust rewrite differs from the upstream
Python [mal-toolbox](https://github.com/mal-lang/mal-toolbox), both by
deliberate scope decision and by behavior, and what's still left to do.
It complements the module-level doc comments in each crate (`//!` at the
top of each file), which have the precise rationale for any one piece —
this file is the cross-cutting summary.

## 1. Scope: what's intentionally excluded

Decided up front, not a gap:

- **`visualization`** and **`translators`** packages — excluded entirely.
- **CLI subcommands** that depend on them: `upgrade-model` (needs
  `translators.updater`), `visualize-model`, and `generate-attack-graph`'s
  `--graphviz`/`--neo4j` flags.
- **`language_graph_from_git_url`** — needs a git clone at runtime; not
  used by anything else in scope.
- Python-specific test categories with no Rust equivalent: pickling
  (`test_attackgraph_pickle`, `test_model_pickle`), `copy.deepcopy`
  semantics (`test_attackgraph_deepcopy`), and tests that mock Python
  internals (`test_attackgraph_init`).

## 2. Architecture: deliberate design differences

These were chosen for Rust idioms, not accidents of translation — see
each crate's module docs for the full rationale.

| Area | Python | Rust |
|---|---|---|
| Graph storage | Live object graph, `ModelAsset`/`LanguageGraphAsset` hold direct references to each other | Arena + generational keys (`slotmap`): `AssetId`/`AttackStepId`/`AttackGraphNodeId` are `Copy` keys into a `SlotMap`, not references |
| `AttackGraph` ↔ `Model` | `AttackGraph.model` is a persistent, mutable reference | `AttackGraph` holds no `Model` reference at all; every method that needs one (`to_dict`, regeneration, name resolution) takes `&Model` explicitly |
| MAL parsing traversal | Raw tree-sitter cursor walk, explicitly skipping `comment` extras (`go_to_sibling`) | tree-sitter's *field* API (`child_by_field_name`/`children_by_field_name`), which never includes `comment` nodes in the first place |
| JSON key order | Python `dict` preserves insertion order by default | `serde_json`'s `preserve_order` feature enabled workspace-wide, to match Python's dict-order-dependent wire format |
| Semantic analysis | Stateful visitor hooked into the same incremental tree-sitter walk as the compiler (`mal_analyzer.py`), accumulating state dicts node-by-node | A single, separate post-pass (`compiler::semantic::analyze`) over the already-compiled langspec, re-deriving the same inheritance-aware step/field/variable resolution Python's incremental hooks got for free |
| Expression chains | One dataclass (`ExpressionsChain`) with many `Optional` fields, validated post-hoc | A Rust `enum` with one variant per shape (`Binary`/`Field`/`Transitive`/`SubType`/`AssocOp`/`Multiplicity`), so each variant only carries the fields it needs |
| Own + inherited accessors | Python `@property`/`@cached_property` on the object itself (e.g. `attack_step.children`) | Rust methods take `&LanguageGraph` explicitly (e.g. `step.children(&graph)`), since the step doesn't hold a reference to the graph it lives in |

## 3. Behavioral divergences from Python — ported faithfully, not "fixed"

This project's mandate is wire/behavior compatibility, so where the real
Python implementation has a quirk or a bug, it was reproduced rather than
corrected, and documented at the site:

- **Model metadata key mismatch** (`maltoolbox-model/src/file.rs`):
  `to_dict` writes `"MAL-Toolbox Version"` (hyphenated); `_from_dict`
  reads `"MAL Toolbox Version"` (spaced). The field never actually
  round-trips in the real Python package either — replicated as-is.
- **Mutual two-file `include` doesn't raise** (`maltoolbox-language/src/
  compiler/mod.rs`): `mal_compiler.py`'s own `visited_files` dedup
  intercepts a repeated include *before* `mal_analyzer.py`'s
  `_include_stack` cycle-detection logic ever runs, so a genuine
  mutual-include cycle silently compiles in the real implementation.
  Confirmed by running the Python oracle, not assumed from reading the
  source.
- **Two cosmetic `mal_analyzer.py` warnings deliberately not ported**:
  "abstract asset never extended" and "duplicate CIA classification" are
  both pure `logger.warning` calls with no effect on whether compilation
  succeeds or on any serialized output, so they were left out rather than
  built as dead weight.
- **`*` transitive-closure operator doesn't actually iterate** (upstream
  bug, not ported as a fix — see §4 below).
- **Partial-regeneration asset-removal ordering contract**
  (`maltoolbox-attackgraph`): Python's object-reference model lets
  `Model.remove_asset` happen before or after
  `AttackGraph.partially_regenerate_graph` interchangeably, because a
  removed `ModelAsset` object is still fully readable even after being
  dropped from `Model.assets`. This port's `AttackGraphNode.model_asset`
  stores only an `i64` id, so the order is now load-bearing: associations
  must be disconnected, then `partially_regenerate_graph` called, and
  only *then* should `Model.remove_asset` run. Self-documented at the
  call site, not inherited for free the way it was in Python.

## 4. Known upstream findings (reported, not silently patched)

Two issues were found in the *Python original* while porting, both
confirmed by running the real implementation rather than inferred from
source alone, and neither "fixed" in this port — see each for why:

1. **`tree-sitter-mal` 1.3.0 can't parse unlabeled detector context.**
   `! logExploit (step) [tpr: 0.1]` (no label before the rate clause)
   parses under the PyPI `tree_sitter_mal` 1.3.0 wheel but fails — a
   missing/error node — under both the crates.io `tree-sitter-mal` 1.3.0
   crate and a from-source build of the `v1.3.0` git tag itself. Four
   tests in `maltoolbox-language/tests/test_detectors.rs` are
   `#[ignore]`d with this reason, not deleted, so they start passing the
   moment the grammar is fixed.
2. **`assoc_traversal_processor.py`'s `_glob_assoc_traversal` (MAL's `*`
   operator in dynamic sentences) never actually computes a transitive
   closure.** Its `while` loop recomputes both `next_assets` and every
   iteration's `new_assets` from the same unchanging
   `instigating_assets` parameter instead of feeding the growing result
   back in, so despite the loop shape it always resolves to exactly one
   application of the pattern. Ported bug-for-bug in
   `maltoolbox-language/src/graph/assoc_traversal.rs` as a single
   direct call with a comment explaining why, rather than reproducing a
   dead loop that would look like a mistake in *this* port.

Both are good candidates to report upstream.

## 5. Two real porting bugs caught before landing (for context)

Not divergences — these were mistakes in the Rust translation itself,
caught by diffing against the running Python oracle before being
committed:

- `quantity_filter` (a multiplicity qualifier like `field:4..10`) is a
  field on *all three* traversal-chain element types in Python
  (`AssocTraversal`/`GlobAssocTraversal`/`AssocSet` are all NamedTuples
  with it as their last field) — an early draft only applied it to plain
  field traversals, which broke on `multiplicity_lang.mal`'s `createFile`
  step (the multiplicity there lands on a set-difference, not a field).
- A step-expression multiplicity's `min`/`max` are raw strings (the
  compiler only normalizes *association* multiplicities, not
  step-expression ones) — Python's `int(x)`-based parser tolerates this
  silently; an early draft assumed already-numeric JSON and silently
  dropped the filter.

## 6. Testing methodology

Every ported component was verified against a real, running Python
mal-toolbox (installed in a scratch venv), not hand-asserted from reading
the source: either by diffing serialized output directly
(`serde_json::Value` equality against Python-generated golden JSON — see
`*_golden.rs` in each crate), or by running small hand-written `.mal`
snippets through both implementations and checking they agree on
success/failure. This caught every divergence and bug listed in §3–§5.

Current status: **109 passing tests, 4 `#[ignore]`d** (all four for the
single upstream grammar gap in §4.1).

## 7. What's left to do

- **`AttackGraph` deserialization** (`load_from_file`/`from_dict`) is not
  implemented — only `save_to_file`/`to_dict` were ported. Not needed by
  either CLI subcommand (`compile`, `generate-attack-graph`), which only
  ever *write* attack graphs, never read them back in.
- **Python interop (PyO3 bindings)** — explicitly left undecided/deferred
  by the user. The core's public API shape is kept FFI-friendly in case
  bindings get added later, but none exist yet.
- Everything else from the original scope is done: MAL compiler +
  semantic analyzer, `LanguageGraph` builder (including model effects),
  `Model`, `AttackGraph` (full build + partial regeneration), pattern
  finder, file I/O (`.mar`/JSON/YAML), and the `maltoolbox` CLI
  (`compile`, `generate-attack-graph`).

## 8. Minor CLI differences worth knowing about

- `generate-attack-graph` takes an explicit `<output_file>` argument.
  The Python original instead wrote to a `maltoolbox.yml`-configured
  debug path (defaulting to `logs/attackgraph.yml`) as a side effect;
  that config/logging subsystem isn't ported, so an explicit argument
  replaces an otherwise-silent write target.
