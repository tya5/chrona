# Design Correction — All Preset Defaults Use Lane Rows; Preserve Editorial Reference (#467, #498)

**Corrects:** [#467 lane design](issue-467-collision-aware-lane-rows-design-2026-09-26.md), [View v0.27 clarification](issue-467-view-v027-contract-clarification-2026-09-27.md), and the [#467–#498 decision plan](../planning/active/issue-467-498-editorial-lane-default-design-plan-2026-09-27.md). **Owner decision:** all packaged presets become lanes; retain the Editorial reference under a separate gallery name (received in this conversation, 2026-09-27). **Baseline:** published `main` at `a28793e2`, with L1/L2 and staged L3a/L3b documents present. **Review:** [whole-architecture review](../reviews/current/issue-467-498-editorial-lane-default-architecture-review-2026-09-27.md). **Implementation:** [L3c amendment](../planning/active/issue-467-494-l3c-preset-default-migration-implementation-amendment-2026-09-27.md).

## Decision and issue contract

Every one of the seven entries in `src/chrona/resources/presets/library.yaml`, plus the separate bundled-default selector `chrona-default-draft`, uses a lane View. These are the eight packaged preset selections at this baseline. This implements #467's literal acceptance row 5 without an Editorial exception. The `editorial` preset alias continues to identify the reusable Editorial appearance; its member points to a newly versioned lane View resource.

The reference-faithful Editorial table treatment remains independently renderable under the gallery name `Editorial Reference`. At this baseline, `13-gallery-editorial` points to `views/editorial.yaml` (`chrona-preset-editorial`) with token `example-v1`, no View `contentIdentity`, and source SHA-256 `e8bcbbab4134a6b4f596cace618bde0c6b02484785bc07df8b225b9c506f0e8b`. The local materializer reads the current address and copies those bytes under the token; it does not resolve an old Git revision. Keep the package and corpus reference Views at their existing paths and IDs without modification. Add a new catalogue lane View at `src/chrona/resources/presets/bundles/editorial/view-lanes.yaml`, ID `chrona-preset-editorial-lanes`, and point the `editorial` catalogue entry at that ID/path. Add its byte-identical corpus mirror `examples/halcyon-1/views/editorial-lanes.yaml`; Context 16 (`gallery-editorial-lanes`) uses this new resource. This leaves Context 13, its resource closure, and its generated Scene/SVG untouched; the lane gallery has distinct View, Context, slide, and output identities.

The bundled default and the `chrona init` starter also use an Editorial-derived lane View and Theme. They retain the #498 readability intent: every item name is visibly placed in its own lane, lane bands guide the eye across the plot, and the default retains Editorial palette, typography, and axis. Lane labels include title and selected finish delta, use visible-overflow and are required Layout text. Names cannot be suppressed in lane mode. The lane table shows the declared group/lane identity and optional count; it does not restore per-item subject columns. The existing #498 acceptance evidence remains an immutable record of the prior accepted resource versions and remains addressable in its acceptance review. The L3c release must add current bundled-default and starter checks and visually compare the new Editorial lane treatment against the unchanged `13-gallery-editorial` reference, whose gallery title is `Editorial Reference`.

The View schema remains v0.27. No schema or runtime behavior beyond the existing lane contract is introduced by this decision. `automatic` remains available for Views that require one item per row, including hierarchy slide 06.

## Literal acceptance criteria to carry forward

From [#467](https://github.com/tya5/chrona/issues/467), preserve each criterion verbatim:

1. “A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.”
2. “Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.”
3. “Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.”
4. “Deltas remain visible for packed items that have them.”
5. “New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.”
6. “At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.”

Criterion 6's examples are non-binding; the selected design excludes hierarchy from lane mode, so use 01, 02 and an accepted non-hierarchy third slide. The named 4wd chain, ≤12 lanes, route counts, and all other literal criteria remain unchanged.

From [#498](https://github.com/tya5/chrona/issues/498), the already accepted four rows remain historical acceptance evidence. L3c adds an explicit current-resource revalidation gate without rewriting their historical disposition:

1. “A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed.”
2. “The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test.”
3. “The same holds for the `chrona init` starter.”
4. “The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis.”

For row 1 in lane mode, “row” means the item's completed lane. Every selected item's title is required text and remains visible; explicit suppression is not a lane-mode success. Row 4 keeps the literal reference label `13-gallery-editorial`; its gallery display name becomes `Editorial Reference`, and the lane gallery uses its own Context and generated outputs.

## Exact resource and identity migration map

The catalogue currently contains seven entries, distinct from the separate wheel-owned `chrona-default-draft` selector. All seven catalogue Views and the selector View move to the v0.27 lane contract. Their non-View bundle members, IDs, compatible schemes, and `gallerySet` assignments stay stable unless a row below names a Context/gallery addition.

| Catalogue preset | Current View member | L3c View disposition | Other catalogue members |
|---|---|---|---|
| `mission-light` | `presets/bundles/mission-light/view.yaml` (`chrona-preset-mission-light`) | lanes; add laneTable, required title+finishDelta plot labels, visible-overflow | Theme, Layout, Scheme unchanged |
| `control-room-dark` | `presets/bundles/control-room-dark/view.yaml` (`chrona-preset-control-room-dark`) | lanes; same lane contract | Theme, Layout, Scheme unchanged |
| `print-mono` | `presets/bundles/print-mono/view.yaml` (`chrona-preset-print-mono`) | lanes; same lane contract | Theme, Layout, Scheme unchanged |
| `executive-light` | `presets/bundles/executive-light/view.yaml` (`chrona-preset-executive-light`) | lanes; same lane contract | Theme, Layout, Scheme, Detail Profile unchanged |
| `elevated-light` | `presets/bundles/elevated-light/view.yaml` (`chrona-preset-elevated-light`) | lanes; same lane contract | Theme, Layout, Scheme, Detail Profile and preferred visual profile unchanged |
| `editorial` | existing `presets/bundles/editorial/view.yaml` remains the reference (`chrona-preset-editorial`); add `presets/bundles/editorial/view-lanes.yaml` (`chrona-preset-editorial-lanes`) | catalogue member changes to the new lane View path/ID; legacy `view.yaml` remains available to reference Contexts | Theme, Layout, Scheme, Detail Profile unchanged; add distinct lane gallery Context |
| `technical-print` | `presets/bundles/technical-print/view.yaml` (`chrona-preset-technical-print`) | lanes; same lane contract | Theme, Layout, Scheme, Detail Profile unchanged |
| `chrona-default-draft` selector | `presets/bundles/editorial-readable-default/view.yaml` (`chrona-preset-editorial-readable-default`) | lanes; add laneTable, required title+finishDelta plot labels, visible-overflow | Editorial-derived readable-default Theme remains separately identified and supplies faint warm lane guides; Scheme, Layout, Detail Profile stay pinned by `presets/default.yaml` |

That table has seven rows because the current source inventory at baseline is not the same as the old plan's five-preset inventory: `library.yaml` has seven entries. The acceptance and resource inventory must be corrected against the published file before implementation; do not invent an eighth catalogue entry to match the handoff plan's “eight”. The eighth lane-bearing packaged View is the default selector's own `editorial-readable-default` bundle, documented separately below. Thus “all eight packaged preset Views” means the seven catalogue View members plus the one selector View, and all eight are lane Views.

The default selector is `src/chrona/resources/presets/default.yaml` (`chrona-default-draft`). Its View stays at `bundles/editorial-readable-default/view.yaml` with the existing resource identity; its content migrates to lane mode with `laneTable`, required title+finishDelta plot labels, and visible-overflow. Its Theme remains separately identified and is retuned only as needed to supply faint warm lane/row-band paint while retaining palette, typography, and axis. The package default and corpus mirror under `examples/halcyon-1/views/` and `themes/` remain byte-identical. The wheel-owned init starter continues to resolve through this selector and is regenerated from the same effective View/Theme. The new-View authoring template/factory must emit lane mode; `automatic` remains an explicit opt-out. The existing `default-draft` sample is separately pinned, not an implicit schema default, and is not evidence for new-View defaults.

Context and gallery map:

| Context/evidence identity | Migration |
|---|---|
| `01-mission-brief` | Adopt lanes only after per-item routes, names, deltas, and reading order pass; use current `mission-light` selection as source if the current slide shares it. |
| `02-programme-board` | Lane acceptance target; migrate after current 4wd ≤12-lane, chain, labels/deltas, and route-cause gates pass. |
| `11-overlay-briefing`, `12-glyph-gates` | Both reuse the 02 View today; migrate with that View, verify each actual Context closure and no route crossing. |
| Third committed lane slide | Select 03 or 04 only after evidence; preserve its current preset appearance and Context identity while migrating its View to lanes. Do not migrate hierarchy 06. |
| `13-gallery-editorial` / slide `gallery-editorial` | Keep Context, View, Theme/Scheme/Layout/Detail and generated Scene/SVG/PNG exactly unchanged; set only the gallery entry title to `Editorial Reference`. |
| `16-gallery-editorial-lanes` (`gallery-editorial-lanes`) | Add a new manifest slide and Context using the `editorial` catalogue's lane View and its existing Theme/Scheme/Layout/Detail closure, with its own generated Scene/SVG/PNG and provenance. |
| `chrona-default-draft` and initialized starter | Point to the Editorial lane-default View/Theme; regenerate bare HALCYON and `chrona init` output, Scene/SVG/PNG, and comparison boards. |

The current inventory has seven catalogue entries and one separate default selector: these are the requested eight preset selections. `library.yaml` remains the authority for catalogue membership; no new selector is added. The `13-gallery-editorial` reference Context and artifacts stay unchanged, with a separate human-facing gallery title. The lane rendering uses `gallery-editorial-lanes` and `16-gallery-editorial-lanes`, resolving `chrona-preset-editorial-lanes` from `views/editorial-lanes.yaml`. Gallery links and manifest IDs must not alias the lane rendering to the reference identity.

## Ownership, failures, and compatibility

View declares lane mode, selection, grouping, ordering, table summary and required label content. Theme and Color Scheme own palette, row-band paint, typography and semantic paint values. Layout owns the one finite lane plan, text measurements, lane identity/order, row extents, item placement, relation routing, overflow, and diagnostics. Scene carries completed lane cells, marks, names, deltas, row guides and routes. Adapters serialize the Scene and do not repair labels or routes. Context pins exact View/Theme/Scheme/Layout/Detail and environment resources; it is not rewritten in place when its rendering role changes.

Lane mode fails closed for invalid lane tables, missing required names/deltas, non-finite geometry, unstable inline geometry, or missing eligible source facts. It may use the already-designed visible-overflow terminal name placement. It does not silently fall back to `automatic`, suppress a name, restore item-subject table columns, exempt a dependency from label obstacles, or reroute in an adapter. `automatic` retains its v0.27 output for unchanged Views. Existing immutable contexts that intentionally use automatic rows remain reproducible.

## Normative and successor records

Update Specification 38 §3.1 to state that the eight packaged View members at this baseline, including the default selector View, adopt lanes when L3c publishes; automatic is an explicit opt-out and hierarchy remains outside lane mode. Update Specification 58's gallery identity contract to keep reference and lane entries distinct and corpus-pinned. No ADR is needed: this is a versioned View-resource migration using the existing #467 contract and existing gallery identity model, not a new ownership or identity mechanism.

## Design evidence required before L3c code

The linked architecture review must validate this map against current schemas, seven actual library records, the default selector, all candidate Context closures, #498 acceptance evidence, and the entire layer model. The implementation amendment must replace the stale “five presets” wording and keep this correction authoritative. If any catalogue entry is absent from the migration table or any Context's effective resource closure cannot be identified, implementation pauses for a new design amendment rather than assuming an implicit alias.
