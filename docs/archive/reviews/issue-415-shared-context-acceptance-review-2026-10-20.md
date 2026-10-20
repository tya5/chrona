# Issue 415 — shared Context acceptance

Feature source: `3a30b154c18bf697d035f37183368100a2662595`,
[PR1800](https://github.com/tya5/chrona/pull/1800), merged at
`cd7dda5f594a65b296f1417f34dbc4676748f8e8`.
Trusted ready main: `e965de32769ec18a9ab8da6e80540bc427b6aac4`.
Feature PR, reviewer migration and exact-main release passed. Approved contract:
[Spec40 §7](../../specification/40-example-reproducibility-and-materialization.md#7-shared-deck-context-authoring-415),
[reviewer approval](https://github.com/tya5/chrona/issues/415#issuecomment-6282070481).
The final pre-code plan was published at `a1dfcdbbd559c30fee10267dbf3ed1185d3ba23c`.

| Literal criterion | Status | Direct evidence |
| --- | --- | --- |
| A deck declares its shared presentation once, and a slide states only what differs. | met | `tests/unit/chrona/usecases/test_deck_context_composition.py`: completed ordinary Contexts from defaults and slide differences. |
| Changing the theme of an eleven-slide deck is one edit. | met | Same module: eleven distinct Context IDs receive one shared theme edit; an unrelated deck is unchanged. |
| The corpus decks are expressed this way, and their rendered output is unchanged. | met; released | [Reviewer row3 evidence](https://github.com/tya5/chrona/issues/415#issuecomment-6284694770) identifies the HALCYON19/roadmap5 migration cohort in [PR1806](https://github.com/tya5/chrona/pull/1806).24/24 composed documents equal their former explicit documents; all50 public SVGs are unchanged. Mission-brief deliberately stays explicit for documented Store addressing. Other corpus decks retain explicit Contexts; this does not claim they migrated. |
| A deck file plus slides that state only their differences render byte-identically to today's fully explicit Contexts (synthetic test). | met | `tests/integration/test_shared_deck_context.py`: actual materialization compares exact Context reference/hash, SVG, Scene and closure bytes at the same owned address. No provenance fields are excluded. |
| Override precedence and an unknown or duplicate key are pointed diagnostics. | met | Composer unit modules cover finite precedence/atomic replacement/null and source origins; `test_shared_deck_context_diagnostics.py` exercises actual CLI and standalone duplicate diagnostics and malformed manifest admission. |
| Measured on HALCYON-1: the reduction in Context lines once the reviewer migrates the examples, and the count table (expected 0 output changes). | met; released | Same-cohort nonempty Context lines: HALCYON2587→1117 (−57%), roadmap822→286 (−65%). PR1806's24-row table and official artifact below prove0SVG/geometry/paint/diagnostic changes;23 Scene changes contain only the approved Context-provenance identity leaf. |

Architecture: one application composer completes Context bytes before immutable
closure; every deck consumer shares it. Layout/Scene/adapters/resource pins are
unchanged. Init retains provider deferral and package closure; transient staging
cannot shadow resources or leak overlays. Explicit YAML bytes/merge syntax stay
unchanged; strict YAML admission is scoped to manifests.

The [final PR run39364863475](https://github.com/tya5/chrona/actions/runs/39364863475)
passed all three pytest shards, conformance, newest-Python reproduction and MCP.
Official artifact12239450326 (SHA256
`ae73a4b4aeb352a5fc19b93e522cfc8542e38568742710db46b4db703ef8a9e3`)
contains50 unchanged SVG and50 unchanged Scene files. Only diagnostic/value
reports differ: moved source anchors and22 added diagnostic sites (20 composer,
2 materialization collisions), no removed normalized sites.
The [native release39366776524](https://github.com/tya5/chrona/actions/runs/39366776524)
on exact review-containing ready main above completed successfully: Ubuntu,
macOS and Windows full pytest/conformance/wheel checks, newest-Python and MCP.
Migration PR1806 merged at `b9342bc973498cca0e042bc335ddfe55ff1db3c8`;
final head `d9bdfc7f120ded19bac108a8c262cad979a5fee8` includes trusted ready
`1a01c9a30bfd753935ce685b46c6b757c97eea08` and passed
[CI39377438413](https://github.com/tya5/chrona/actions/runs/39377438413).
Official artifact12244247134 ZIP SHA256
`16d3565a25976c83c2665b574029f2d48ea8a76c31b460d1219e9459b0215d6a`
has109 safe paths, identical before/after path sets and0 retirements:
all50SVG/9reports byte-identical;23of50Scenes each change exactly one
`provenance.resources[kind=render-context].contentIdentity` leaf, no other leaf.
Coordinator and independent Luna audits agree. Context equivalence is24/24;
focused composition/role-admission/init/render-review controls passed109 tests,
and integration with B1805 passed17 authoring/lifecycle/guide tests.
No new composer, public transient address, schema or layer ownership was added.
The line-count table distinguishes flow-style savings from sharing alone;
HALCYON/roadmap block-style totals would be1567/443. The exact
review-containing main `37b3f5a988833b929509dfee3224e285bc2d51b2` passed
[release39382911887](https://github.com/tya5/chrona/actions/runs/39382911887):
all three OS full pytest/conformance/wheel, MCP floor and newest-Python
reproduction. The release and reviewer-selected cohort were accepted in
[the closing review](https://github.com/tya5/chrona/issues/415#issuecomment-6286050198).
