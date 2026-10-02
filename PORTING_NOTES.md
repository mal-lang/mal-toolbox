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

- **Cosmetic compiler warnings, surfaced without a logging framework**
  (`maltoolbox-language/src/compiler/{mod.rs,semantic.rs}`):
  `mal_analyzer.py`'s two advisory-only `logger.warning` calls - "abstract
  asset never extended" (`semantic.rs::warn_abstract_never_extended`) and
  "duplicate CIA classification" (`mod.rs::visit_cias`) - are ported, but
  printed with plain `eprintln!` rather than routed through a logging
  crate, since this project doesn't port Python's `logging`/
  `maltoolbox.yml` config subsystem (see §7). Neither warning affects
  compilation success or serialized output in either implementation; the
  duplicate-CIA one in particular is detected during the raw tree-sitter
  walk in `mod.rs`, not in `semantic.rs`'s later pass over the compiled
  langspec, since by that point the `risk` flags are already deduplicated
  booleans and the repeated letter is no longer visible.
- **`RemovedAssetSnapshot` avoids a dangling-id trap in partial
  regeneration** (`maltoolbox-model/src/model.rs`,
  `maltoolbox-attackgraph/src/{graph.rs,partially_generate.rs}`):
  Python's object-reference model (see the "Graph storage" row above)
  lets `Model.remove_asset` run before or after
  `AttackGraph.partially_regenerate_graph` interchangeably, because a
  removed `ModelAsset` object is still fully readable even after being
  dropped from `Model.assets`. This port's `AttackGraphNode.model_asset`
  stores only an `i64` id, so naively porting this would make call order
  load-bearing: `partially_regenerate_graph` would need to look a removed
  asset up by id in `model` to resolve its language type/name, which only
  works *before* `Model.remove_asset` deletes it. Rather than document
  that as a contract, `Model.remove_asset` now returns a
  `RemovedAssetSnapshot { name, lg_asset }` - captured at the one moment
  this port can still cheaply answer "what was this asset" - and
  `partially_regenerate_graph`'s `removed_assets` parameter carries one
  per id instead of a bare `HashSet<i64>`. Every lookup that used to need
  `model.get_asset_by_id` for a possibly-removed id now reads the
  snapshot instead, so the two methods can be called in either order with
  no efficiency cost (no scanning; same O(1) lookups as before, just
  sourced from the snapshot instead of a live `model` query).

## 3. Confirmed upstream bugs fixed, not reproduced

Unlike the deliberate design differences in §2, these are cases where an
upstream dependency or the Python oracle's behavior was confirmed buggy
and this project fixed it rather than working around or reproducing it,
since silently under-resolving or dropping data (or staying pinned to a
broken parser) seemed worse than wire-compatibility here. Documented at
the site in both implementations:

- **`tree-sitter-mal` 1.3.0 can't parse unlabeled detector context —
  fixed upstream in 1.3.1.** `! logExploit (step) [tpr: 0.1]` (no label
  before the rate clause) parsed under the PyPI `tree_sitter_mal` 1.3.0
  wheel but failed — a missing/error node — under both the crates.io
  `tree-sitter-mal` 1.3.0 crate and a from-source build of the `v1.3.0`
  git tag itself. Four tests in `maltoolbox-language/tests/
  test_detectors.rs` were `#[ignore]`d with this reason rather than
  deleted; the workspace now pins `tree-sitter-mal = "1.3.1"`, the four
  tests pass unmodified, and the `#[ignore]` attributes have been
  removed.
- **`*` transitive-closure operator didn't actually iterate**
  (`maltoolbox-language/src/graph/assoc_traversal.rs`,
  `glob_assoc_traversal`): `assoc_traversal_processor.py`'s
  `_glob_assoc_traversal` recomputes both its seed and every loop
  iteration from the same unchanging `instigating_assets` instead of the
  growing result, so despite the while-loop shape it always resolves to
  exactly one application of the pattern rather than a real closure.
  Confirmed against the running Python oracle. The Rust port implements
  an actual fixed-point closure, feeding the growing result back into the
  pattern traversal each iteration.
- **Model metadata key mismatch** (`maltoolbox-model/src/file.rs`):
  `to_dict` (`model.rs`) writes `"MAL-Toolbox Version"` (hyphenated), but
  `_from_dict` in the Python original reads `"MAL Toolbox Version"`
  (spaced), so the field never actually round-trips there and silently
  falls back to the running tool's own version. The Rust port's
  `from_dict` reads the same hyphenated key `to_dict` writes, so the
  field round-trips correctly.
- **Mutual two-file `include` doesn't raise** (`maltoolbox-language/src/
  compiler/mod.rs`): `mal_compiler.py`'s own `visited_files` dedup
  intercepts a repeated include *before* `mal_analyzer.py`'s
  `_include_stack` cycle-detection logic can see it, and that same
  dedup also means a cycle looping back to the *root* file is never
  caught even when `_include_stack` itself does run, since the root is
  never pushed onto it as an include target in the first place - only
  files reached via an `include_declaration` are. A genuine two-file
  mutual include (A includes B includes A) therefore silently compiles
  in the real implementation. Confirmed by running the Python oracle,
  not assumed from reading the source. The Rust port tracks the active
  include chain (`compile_inner`'s `active` parameter) and raises a
  `CompileError::Semantic("Include sequence contains cycle: ...")` for
  any real cycle, while still allowing non-cyclic repeated includes
  (a "diamond": both B and C include A) to compile once and short-circuit
  on the repeat, same as before.

## 4. Two real porting bugs caught before landing (for context)

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

## 5. Testing methodology

Every ported component was verified against a real, running Python
mal-toolbox (installed in a scratch venv), not hand-asserted from reading
the source: either by diffing serialized output directly
(`serde_json::Value` equality against Python-generated golden JSON — see
`*_golden.rs` in each crate), or by running small hand-written `.mal`
snippets through both implementations and checking they agree on
success/failure. This caught every divergence and bug listed in §2–§4.
Note that §3's fixes (`glob_assoc_traversal`, model-metadata round-
tripping, and include-cycle detection) make this port genuinely
*intentionally* diverge from the Python oracle's output for those three
cases — they'll disagree with Python by design.

Current status: **114 passing tests, 0 `#[ignore]`d**.

## 6. What's left to do

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

## 7. Minor CLI differences worth knowing about

- `generate-attack-graph` takes an explicit `<output_file>` argument.
  The Python original instead wrote to a `maltoolbox.yml`-configured
  debug path (defaulting to `logs/attackgraph.yml`) as a side effect;
  that config/logging subsystem isn't ported, so an explicit argument
  replaces an otherwise-silent write target.
