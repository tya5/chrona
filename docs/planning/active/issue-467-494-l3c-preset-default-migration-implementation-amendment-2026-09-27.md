# Implementation Amendment — L3c Preset and Default Migration (#467, #494, #498)

**Amends:** [L3 publication ladder](issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md). **Design:** [L3c correction](../../design/issue-467-498-editorial-lane-default-design-correction-2026-09-27.md). **Review:** [whole-architecture review](../../reviews/current/issue-467-498-editorial-lane-default-architecture-review-2026-09-27.md). **Normative authority:** [Specification 38](../../specification/38-review-row-composition.md) and [Specification 58](../../specification/58-example-roles-and-evidence.md). **Plan base:** published `main` at `a28793e2`. **Status:** planning only; L3c product edits wait for accepted L3b evidence and publication of its design/review.

## Literal acceptance

Carry forward each #467 criterion verbatim:

1. “A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.”
2. “Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.”
3. “Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.”
4. “Deltas remain visible for packed items that have them.”
5. “New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.”
6. “At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.”

Keep every #494 route acceptance criterion and all four literal #498 rows; their full text is in the linked design correction. The accepted #498 review remains the record for the prior default resource version. This amendment adds current-default/starter revalidation after migration.

## Exact eight-View inventory

At `a28793e2`, `library.yaml` has seven catalogue entries; `presets/default.yaml` selects the separate eighth View. Migrate all eight Views to v0.27 lanes. Preserve every non-View member, ID, compatible scheme, visual profile and gallerySet unless listed here:

| View | Path | Migration |
|---|---|---|
| `mission-light` | `presets/bundles/mission-light/view.yaml` | Lane table; required title and promised delta; visible overflow |
| `control-room-dark` | `presets/bundles/control-room-dark/view.yaml` | Same lane contract |
| `print-mono` | `presets/bundles/print-mono/view.yaml` | Same lane contract |
| `executive-light` | `presets/bundles/executive-light/view.yaml` | Same lane contract |
| `elevated-light` | `presets/bundles/elevated-light/view.yaml` | Same lane contract |
| `editorial` | Add `presets/bundles/editorial/view-lanes.yaml` (`chrona-preset-editorial-lanes`); keep existing `view.yaml` (`chrona-preset-editorial`) as reference | Update only the catalogue View member ID/path; point Context 16 at byte-identical corpus mirror `views/editorial-lanes.yaml` |
| `technical-print` | `presets/bundles/technical-print/view.yaml` | Same lane contract |
| `chrona-default-draft` | `presets/bundles/editorial-readable-default/view.yaml`, selected by `presets/default.yaml` | Lane contract; retain selector ID and Editorial-derived Theme, retuned only for admitted guide/lane roles |

The eight selected preset Views must be explicit: add `rows.laneTable`, required plot titles, selected finish deltas where the source promised them, `placement: plot`, and `overflow: visible-overflow`. No item-subject `tableColumns` in lane mode. Keep `automatic` an explicit opt-out. Locate each new-View creator/template and have it emit `lanes`; do not infer a schema default. Update package/corpus mirrors byte-identically, including new Editorial lane source/mirror paths. Keep the existing Editorial reference resource and corpus mirror unchanged.

The catalogue/resource migration is supported by the current resolver: `preset_library._copy_member` loads the entry's `sourceRoot` + `sourcePath` and checks the resource envelope ID against the member ID. No code requires a member path to be named `view.yaml` or requires the `editorial` alias to retain its old View ID. Update `tests/integration/test_public_preset_evidence.py`'s hard-coded editorial source-path assertion and corpus-mirror pair to `view-lanes.yaml`/`views/editorial-lanes.yaml`; retain its direct-render and byte-copy checks for `view.yaml`/`views/editorial.yaml` as reference checks. Add `view-lanes.yaml` to the packaged-resource inventory test and `views/editorial-lanes.yaml` to `examples/reachability.yaml`.

Context and evidence identities:

| Identity | Required disposition |
|---|---|
| `01-mission-brief`, `02-programme-board` | Candidate lane slides; retain current project and presentation closure except the approved View migration |
| `11-overlay-briefing`, `12-glyph-gates` | They reuse the 02 View; migrate with it and independently inspect actual Context routes/labels |
| third committed slide | Choose eligible non-hierarchy 03 or 04 after route and reading-order evidence; keep 06 automatic |
| `13-gallery-editorial` / slide `gallery-editorial` | Keep Context, View, Theme/Scheme/Layout/Detail and generated Scene/SVG/PNG byte-identical; add gallery title `Editorial Reference`. |
| new slide `gallery-editorial-lanes`, Context `16-gallery-editorial-lanes` | Add distinct Context/slide/generated Scene/SVG/PNG for catalogue `editorial` lane View |
| `chrona-default-draft` / fresh `chrona init` | Use the same default lane View/Theme closure; regenerate bare CLI outputs |

`docs/gallery/example-gallery.yaml` must declare separate `Editorial Reference` and `Editorial Lane` entries with distinct slide provenance. The two gallery peers use the same Project and environment. Do not repoint the old Context or reuse its slide ID for lane output.

## Slices and gates

| Slice | Files and owners | Evidence | Publish gate |
|---|---|---|---|
| L3c-1: close prerequisites | Inventory all eight closures and every new-View producer; no resource edits | Current-base L3b 02 lane count/membership/chain; 02/11/12 route causes and no crossings; candidate third-slide review | If 02 exceeds 12 lanes, chain fails, or required labels/routes fail, return to design before activation |
| L3c-2: View/default migration | Seven catalogue View YAMLs, default View, new-View template, corpus mirrors and closure tests | Schema and packaged-closure checks for all eight; each item title/delta visible in its own lane; table facts removed/moved documented; unchanged automatic bytes characterized | All eight resolve from packaged resources; no hidden workspace-only input; publish resource changes separately |
| L3c-3: reference and lane gallery | Leave package/corpus reference View and Context 13 untouched; add `view-lanes.yaml` and `views/editorial-lanes.yaml` with new ID; add slide/Context 16; update gallery catalogue and manifest | Prove package/corpus lane file byte identity; materialize both Contexts; compare same Project/environment; inspect slide 13 for no changes and slide 16's Scene/SVG/PNG | Slide 13 hashes remain unchanged. Lane gallery owns a distinct View, Context, slide and artifact identity. |
| L3c-4: public defaults and corpus | Bundled default, starter, lanes on 01/02/eligible third, 11/12 with shared View; leave 06 automatic | Bare HALCYON CLI and fresh init CLI, Scene/SVG/PNG; own-lane name/delta and guide checks; Editorial palette/type/axis; compare to slide 13; route and public materializer checks | All six #467 rows plus current #498 readability rows pass; regenerate and review evidence as one batch |
| L3c-5: release review | New `docs/reviews/current` acceptance record | Exact commits/commands/CI, literal rows, artifact hashes and diffs, rendered inspection, independent failure disposition | Three-OS conformance/full pytest/wheel-smoke and newest-Python materializer green; publish serially after fetching main |

## Cross-cutting implementation rules

Keep L3a/L3b behavior authoritative. Layout owns one immutable lane plan, text sizing, placement, extents, route obstacles and causes; Scene projects completed geometry; adapters serialize it. Required titles/deltas enter the shared obstacle set before semantic routes. Never suppress a packed name, restore item table columns, exempt labels from routes, or add renderer repair. Recompute old WIP measurements on the accepted current base. All seven catalogue presets need generic closure/render coverage, not one representative preset only. Preserve #498's prior artifact hashes in its historical acceptance record. Preserve slide 13's current bytes; add newly materialized files/hashes for Editorial lane, current defaults and starter. A green test run alone is not acceptance; inspect the emitted SVG/PNG as a batch.

Before publication, fetch and inspect `origin/main`, staged/generated diffs and conflicts, publish in order, verify remote commits and CI. Keep #467/#494 open until every literal acceptance row and release gate is met.
