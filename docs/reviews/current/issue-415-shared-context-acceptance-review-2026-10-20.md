# Issue 415 — shared Context acceptance

Source: `28237eed6e83a841a1030d4ad6e49727ce713f23`.
Feature verification in progress; this is not issue closure. Approved contract:
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
Schema maintenance uses the documented prune: fourteen already-merged stale
L1 allowances retire; only this schema's added marker is new. No corpus source
or generated SVG/Scene/report is authored by the feature.

Required PR snapshot, full CI and exact review-containing main release remain
pending. Keep issue415 open for those gates and reviewer-owned migration.
