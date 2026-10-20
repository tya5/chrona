# Issue 415 — shared Context acceptance

Feature source: `3a30b154c18bf697d035f37183368100a2662595`,
[PR1800](https://github.com/tya5/chrona/pull/1800), merged at
`cd7dda5f594a65b296f1417f34dbc4676748f8e8`.
Trusted ready main: `e965de32769ec18a9ab8da6e80540bc427b6aac4`.
Feature PR verification passed; exact-main release remains pending. Approved contract:
[Spec40 §7](../../specification/40-example-reproducibility-and-materialization.md#7-shared-deck-context-authoring-415),
[reviewer approval](https://github.com/tya5/chrona/issues/415#issuecomment-6282070481).
The final pre-code plan was published at `a1dfcdbbd559c30fee10267dbf3ed1185d3ba23c`.

| Literal criterion | Status | Direct evidence |
| --- | --- | --- |
| A deck declares its shared presentation once, and a slide states only what differs. | met locally | `tests/unit/chrona/usecases/test_deck_context_composition.py`: completed ordinary Contexts from defaults and slide differences. |
| Changing the theme of an eleven-slide deck is one edit. | met locally | Same module: eleven distinct Context IDs receive one shared theme edit; an unrelated deck is unchanged. |
| The corpus decks are expressed this way, and their rendered output is unchanged. | deferred | Reviewer-owned migration follows the feature; do not count existing explicit corpus Contexts as migrated. |
| A deck file plus slides that state only their differences render byte-identically to today's fully explicit Contexts (synthetic test). | met locally | `tests/integration/test_shared_deck_context.py`: actual materialization compares exact Context reference/hash, SVG, Scene and closure bytes at the same owned address. No provenance fields are excluded. |
| Override precedence and an unknown or duplicate key are pointed diagnostics. | met locally | Composer unit modules cover finite precedence/atomic replacement/null and source origins; `test_shared_deck_context_diagnostics.py` exercises actual CLI and standalone duplicate diagnostics and malformed manifest admission. |
| Measured on HALCYON-1: the reduction in Context lines once the reviewer migrates the examples, and the count table (expected 0 output changes). | deferred | After migration, compare the same manifest cohort and count Context-provenance-only Scene changes separately; require zero SVG/geometry/paint/diagnostic changes. |

Architecture review: one application selection/composition owner precedes the
unchanged immutable closure boundary. All inspection consumers share its
document/bytes/provenance, not a second merger or temporary authored Context.
Layout, Scene, adapters and resource pins are unchanged. Init retains provider
deferral and complete package closure; transient staging cannot shadow resources
or leak materializer overlay files into the Store. Explicit YAML bytes and
existing explicit YAML merge syntax remain unchanged. Strict YAML admission is
scoped to manifests. Exceptions retain ordinary traceback mutability without
changing the shared diagnostic envelope.

Local verification includes the real composed/explicit materializer and init
tests, existing materializer/init/font-set regressions (52 passed, one corpus
test deselected), failure-report/transport checks and schema equivalence.
Composer/schema batch: 186 passed; inspection tools and acceptance caller batch:
356 passed, 49 intentional skips (no declared rowIndex column). The optional CJK
provider is installed; it did not cause these skips. Final composer/composition/
malformed-manifest batch: 26 passed, including stable completed-Context error
codes. Package-backed gallery diffs: 4 passed through the normal reference reader.
Final inspector follow-up: 28 passed for immutable mapping viewport derivatives,
shared Store-root propagation and fontSet-expanded identity checks; incorrect
Scene font identities still fail and authored Context payloads remain unchanged.
Schema maintenance uses the documented prune: fourteen already-merged stale
L1 allowances retire; only this schema's added marker is new. No corpus source
or generated SVG/Scene/report is authored by the feature.
Local conformance passed every non-derived-report check, including actual
documented commands. Its only failures were stale CI-owned diagnostic/value
inventories (new diagnostic sites and moved source anchors); CI regenerates and
verifies those reports in the official snapshot, not in authored commits.

CI correction: run39363078550 rejected the prior head only at
`test_schema_loader::test_registry_holds_exactly_the_listed_parts` (shard3) and
`test_schema_identifiers_and_license::test_every_live_id_site_references_identifier_or_is_on_the_documented_allowlist`
(shard2). Exact registry membership now includes both declared target lists;
missing-target detection covers both, and bundling/dereferencing covers the new
schema. Existing deck/slide IDs are explicitly classified; composed IDs reference
the canonical Context ID grammar, with seven equivalence probes. No validator or
assertion was weakened. Related batches passed197 and245 tests; integration with
published1781 passed238 and schema equivalence. The expected-delta conflict was
resolved to preserve main's complete ledger plus this schema's one added marker.

The [final PR run39364863475](https://github.com/tya5/chrona/actions/runs/39364863475)
passed all three pytest shards, conformance, newest-Python reproduction and MCP.
Official artifact12239450326 (SHA256
`ae73a4b4aeb352a5fc19b93e522cfc8542e38568742710db46b4db703ef8a9e3`)
contains50 unchanged SVG and50 unchanged Scene files. Only diagnostic/value
reports differ: moved source anchors and22 added diagnostic sites (20 composer,
2 materialization collisions), no removed normalized sites.
The [native release39366776524](https://github.com/tya5/chrona/actions/runs/39366776524)
on exact ready main above has Ubuntu/macOS success; Windows remains in progress.
Keep issue415 open for that gate and reviewer-owned migration/count table.
