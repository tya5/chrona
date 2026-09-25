# Design — Tooling CI Throughput (#452)

## Decision

Chrona's tooling evidence remains fully recomputed for each invocation, but
each invocation parses each immutable YAML path at most once.  Tooling uses
LibYAML's `CSafeLoader` whenever available, falling back to `SafeLoader` only
where LibYAML is unavailable.  No cache crosses a `render`, `discover`, or CLI
process boundary.

`tools/presentation_coverage.py` owns a small independent `_load` function
using `yaml.load(..., Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))`.
It must not import `chrona.`: it is intentionally able to inspect corpus
evidence without product imports.  All other tools and the one product
importer that used direct `yaml.safe_load` use `chrona.resources.safe_load`,
the existing safe, JSON-aware loader.

## Data flow and cache boundary

```text
tool invocation / one report render
  -> RunLocalYamlLoader[resolved path]   (fresh cache)
  -> CSafeLoader / SafeLoader
  -> validated Mapping
  -> deterministic report or diagnostic
```

The cache key is the resolved `Path`; its value is the successfully parsed
document only.  Reads that fail are not cached, preserving the original
diagnostic and allowing a repaired file to be read in the same process.  A
new public `render(root)` creates a new loader, so test fixtures that rewrite a
path and repeated report calls cannot observe stale bytes.

Semantic-realization coverage obtains `slides = discover(root)` once and
passes that immutable tuple to every family.  Semantic-registry reachability
obtains `reachable = reachable_semantic_ids(root)` once before filtering the
finite registry list.  Neither optimization changes a predicate, ordering, or
the set of production paths traversed.

## Boundaries and invariants

- Tool reports remain deterministic and inspect the same current files.
- Presentation coverage retains its no-product-import/no-renderer/no-SVG
  boundary.
- YAML remains safely loaded; no unsafe loader or global mutable cache is
  introduced.
- Direct `yaml.safe_load` is prohibited under `src/` and `tools/` so the
  performance rule cannot silently drift.  Explicit `yaml.load` requires the
  selected safe loader expression.
- Tests still run all report computations twice; the speed improvement comes
  from cheaper equivalent computation, not from removing that check.

## Whole-architecture consistency review

This is an infrastructure-only change.  Product resource semantics remain in
`chrona.resources`; product code uses that canonical loader.  The exceptional
independent coverage tool preserves its intentionally inverted dependency
direction.  Caches sit below report policy and above parsing, so they cannot
decide coverage, select a renderer, or alter generated evidence.  The change
therefore improves CI throughput without weakening the Project → Layout →
Scene → adapter architecture or reducing the release gate.

## Verification

Characterization tests compare repeated report bytes and current error paths.
New unit tests count reachability traversal and corpus discovery once per
operation, verify a rewritten path is reloaded by a new run, enforce the
loader-source policy, and prove every target continues to receive the same
evidence.  Focused duration measurement is advisory; normal CI remains the
authoritative full-suite validation.
