# Implementation Plan — Semantic-to-Visual Realization (#414, #402, #413)

**Status:** Approved by the published design and architecture reviews.
**Authority:**
`issues-414-402-413-semantic-visual-realization-design-2026-09-25.md`, its
Layout Profile version correction, and both corresponding architecture reviews.

## I414-1 — Deterministic realization evidence foundation

Add the finite realization-family registry under
`src/chrona/presentation/model/`, together with a generator separate from
`tools/presentation_coverage.py`.  The generator consumes only the registry,
normalized corpus declarations, and committed inspection Scenes; it emits a
checked report in `docs/gallery/`.  Add unit tests for deterministic order,
invalid state/semantic declarations, intentional equivalences, selected-but-not-
realized gaps, and no adapter/SVG/pixel dependency.

Update CI to check the new generated report.  Regenerate it without claiming
#402 or #413 as covered before their slices land.

**Acceptance:** report and tests are public, reproducible, and correctly show
the two confirmed gaps.  Focused tool/registry tests, report `--check`, and
conformance pass.  Publish this slice before changing output roles.

## I402-1 — Typed table-cell state closure

1. Introduce a typed table-cell content record in
   `surface_content.py`, `presentation_contract.py`, and `v05_content.py`.
   Migrate all constructors, fixtures, and tests; delete the tuple input.
2. Add the finite source-to-cell-semantic selector specified by the design.
   It consumes column source and projected fact, never `ReviewItem.roles` order
   or displayed text.
3. Require Layout's table `TextPlacement` to preserve the supplied
   `semantic_id`; simplify `v05_builder.py` so its table path calls only the
   registry binding for that identity.
4. Add semantic registry and Theme bindings for `missingActualCell`; retain
   `varianceAhead`, `finishDelta`, and `varianceBehind` for variance output.
5. Extend HALCYON corpus/resource data with ahead, on-plan, behind, unknown,
   observed, and missing examples; regenerate affected Scene/SVG evidence and
   the realization report.

**Acceptance:** focused normalizer/Layout/Scene tests prove every permitted
mapping, neutral custom/title columns, ellipsis identity preservation, and the
absence of Scene ID/content/role-tuple selection.  Public materializer bytes
and the report demonstrate the states.  Run affected materializers, generated
SVG diff review, conformance, full pytest, installed-wheel smoke, and CI before
publishing.

## I413-1 — Layout Profile v0.7 and annotation route isolation

Create `layout-profile-v0.7.schema.yaml`, update schema inventory, runtime
dispatch, closure validation, package/resource tests, conformance fixtures, and
every public profile/context to v0.7.  Add mandatory finite
`annotationRouting` values.  Remove v0.6 reader and schema from the live path.

Update `layout/profile.py`, typed layout profile model, and route-quality calls
so annotation leaders consume the new values and dependency relations consume
only `relationRouting`.

**Acceptance:** v0.6 is rejected; every shipped closure resolves v0.7; direct
tests prove independent policy changes; all existing corpus profiles are
materializable.  Run schema, closure, focused routing, conformance, and full
pytest before publishing.

## I413-2 — Completed annotation presentation

1. Add typed normalized annotation intent and Layout annotation presentation
   mapping for the four finite purposes.
2. Add purpose-specific box/text/leader bindings to the semantic registry and
   Theme resources.  Remove the generic annotation fallback from this surface.
3. Place semantic identities on annotation text, shapes, and leaders; complete
   `explanatory-arrow` marker geometry in Layout using its declared terminal
   role.  Scene must project all three supplied identities verbatim.
4. Add a Controller Z corpus slide that realizes every purpose, verifies an
   arrow marker, and proves independent box/leader treatment.  Regenerate
   public evidence and the realization report.

**Acceptance:** structural tests reject Scene-side identity reconstruction;
focused Layout/Scene/visual-capability tests cover all purposes and marker
admission; materializer output distinguishes the treatments.  Review generated
SVG and run conformance, full pytest, installed-wheel smoke, and CI before
publication.

## I414-2 — Programme release and evidence disposition

Run the complete P3 verification set once after I402-1 and I413-2 are merged:

* realization-report and presentation-coverage checks;
* focused semantic/normalizer/Layout/Scene/report tests and full pytest;
* all affected public materializers, generated Scene/SVG diff review, and
  diagnostics/vocabulary inventories where changed;
* conformance, installed-wheel smoke, and three-platform CI.

Publish an English acceptance review mapping every #414/#402/#413 criterion to
public evidence.  Close an issue only if its report rows have no unresolved
gap; otherwise retain the issue and publish a narrowed follow-up plan.

## Publication protocol

Each slice is one serial fast-forward publication.  Immediately before every
push, fetch `origin/main`, verify the exact ahead/behind range and worktree
diff, then confirm the remote commit after push.  No force push, compatibility
reader, partial resource migration, or adapter-local repair is permitted.
