# #496 Theme asset catalogues implementation plan

**Status:** Ready to start after dependency bases are public.
**Design:** [selected contract](../../design/issue-496-theme-asset-catalogues-design-2026-09-28.md).
**Architecture review:** [approved review](../../reviews/current/issue-496-theme-asset-catalogues-architecture-review-2026-09-28.md).
**Density correction review:** [approved correction](../../reviews/current/issue-496-theme-asset-catalogues-architecture-review-correction-2026-09-28.md).
**Living issue record:** [#496 work record](issue-496-theme-asset-catalogues-work-record-2026-09-28.md).
**Design/correction commits:** `7e2d69bea6aa8ea8a94f7ac3c573b6db910397f9`, `59e3686e4072dadc0a03baa771f45fb7250da7d7`.

Run commands from the repository root with the project's virtual environment
selected. Set `CHRONA_PY` to that environment's interpreter (the current
workspace uses `/Users/yasudatetsuya/Workspace/chrona_dev/coder/.venv311/bin/python`)
and set `PYTHONPATH="$PWD/src:$PWD"` so this worktree is imported. Commands
below use `$CHRONA_PY` to avoid assuming a venv directory inside the worktree.

## Baseline, dependencies, and publication rule

The plan adds no product changes. Before the first implementation commit,
`origin/main` must contain the #505 and #466 bases ordered by #454. At plan
publication, #505 is public in merge commit
`56f657358ce44e0c91e09dceaa87c38e686e06af` (#520); #466 is not yet public.
The design branch and this planning branch are not proof of either dependency.
Start implementation from latest public main only after verifying both
dependencies there. If either is absent, keep this plan published and defer
product work. #464 glyph shapes, #465 PNG annotation art, and #479 preset
detail profiles remain the accepted adjacent contracts.

Publish four coherent units in order: (1) catalogue schema, normalization,
and ingress; (2) Theme binding, closure, completed Scene, and paint gates;
(3) builtin catalogue/preset copy and render closure; (4) user-visible
acceptance review. Each slice is reviewed and published separately. Amend the
design, whole-architecture review, and this plan before resuming if a slice
requires a different owner, public contract, or migration. Do not bundle later
slice changes into an earlier publication.

## Literal issue acceptance

1. “A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice.”
2. “A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint.”
3. “A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags.”
4. “A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile.”
5. “A missing asset reference fails with a Theme pointer and the `set:name`.”

The first four criteria require rendered/catalogue evidence in addition to
focused tests. Criterion 5 requires the exact negative diagnostic. None is met
by this planning publication.

## Slice 1 — catalogue v0.4, normalization, and import

**Owned files and resources:** add `schemas/icon-catalog-v0.4.schema.yaml`
and `schemas/theme-asset-source-v0.1.schema.yaml`; update
`schemas/schema-inventory-v0.1.yaml` and `schemas/README.md`; extend
`src/chrona/presentation/contracts/resources.py` for v0.4;
`src/chrona/presentation/icons/normalizer.py` and `importer.py`; add a bounded
catalogue entry model as needed under `src/chrona/presentation/icons/`; add an
explicit `--theme-assets SOURCE.yaml` mode to the existing
`chrona icon-catalog import` command in `src/chrona/app/cli.py`. Keep current
Iconify JSON ingress behavior. Add committed valid/invalid source fixtures in
`tests/fixtures/icons/` and glyph/pattern coverage in
`tests/unit/chrona/presentation/icons/test_normalizer.py`,
`test_importer.py`, and `tests/unit/chrona/presentation/contracts/test_icon_catalog.py`.

**Migration:** emit/accept `chrona/icon-catalog/v0.4`. Keep the packaged v0.3
Material catalogue, its Context references, and bytes unchanged in this slice;
mark v0.3 `transitioning` to v0.4 in the schema inventory (`successor:
icon-catalog-v0.4.schema.yaml`, `removalSlice:
issue-496-v03-retirement-after-resource-migration`) while its reader remains
available. v0.3 is never
reinterpreted as v0.4. Add both schema versions to
`tests/integration/test_packaged_resources.py`. Record normalization profile
`chrona/theme-asset-normalization/v0.1`, finite limits, arc-to-quadratic
tolerance, tile angle, `densityBasisPoints` integer range 1–10,000, fixed
128×128 center-grid density derivation with periodic wrap and half-up rounding,
and reject-not-repair behavior in schema and diagnostics. The ordered-dither
fixtures must encode 12.5%, 25%, and 50% exactly as 1,250, 2,500, and 5,000
basis points; include mismatching declaration rejection. Licensing stays
explicit SPDX plus complete notice;
catalogue write is atomic.

**Focused checks:**

- `$CHRONA_PY -m pytest tests/unit/chrona/presentation/icons/test_normalizer.py tests/unit/chrona/presentation/icons/test_importer.py tests/unit/chrona/presentation/contracts/test_icon_catalog.py`
- `$CHRONA_PY -m pytest tests/cli/test_cli.py::test_cli_icon_import_diagnostic_identifies_the_rejected_icon_source`
- `$CHRONA_PY tools/validate_schema_references.py` and
  `$CHRONA_PY tools/schema_inventory.py`
- Add positive and negative cases for every glyph/pattern primitive, limits,
  unsupported data, notice/license, canonical output identity, atomic failure,
  alias/set collision, and v0.3/v0.4 separation.

**Generated/review evidence:** canonical source-to-catalogue bytes and SHA-256;
notice bytes; schema inventory; importer CLI help; no partial output after an
invalid mixed catalogue. Do not update rendered examples in this slice.

**Publication boundary:** standalone catalogue/import commit. Catalogues
remain inert until the next slice adds Theme consumers.

## Slice 2 — Theme, resolution, Scene v0.7, and effective paint

**Owned files:** add authored `schemas/theme-v0.13.schema.yaml`, derived
`schemas/theme-v0.14.schema.yaml`, and `schemas/scene-v0.7.schema.yaml`; update
schema inventory/readme and the version dispatch in
`src/chrona/presentation/contracts/resources.py`; extend
`src/chrona/presentation/model/theme_tokens.py`, Theme inheritance, closure
resolution in `src/chrona/presentation/model/closure.py`, and exact
role/property admission in `src/chrona/presentation/scene/capabilities.py`.
Extend glyph resolution and mark fit in
`src/chrona/presentation/layout/lane_mark_facets.py`,
`src/chrona/presentation/layout/mark_geometry.py`,
`src/chrona/presentation/layout/icon_geometry.py`, and their consuming
`surface_composer.py` path (the former `lane_bundle_mapper.py` was removed by
the public #505 refactor). Add a pure
`src/chrona/presentation/layout/pattern_placement.py` for completed tile
origin/region/clip values; refactor `src/chrona/presentation/scene/pattern_geometry.py`
so it no longer derives geometry from Theme tokens. Scene projection in
`src/chrona/presentation/scene/v05_builder.py` consumes Layout's completed
pattern value. Extend typed Scene values and wire serialization in
`src/chrona/presentation/scene/model.py` and
`src/chrona/presentation/scene/serialization.py`; update SVG serialization in
`src/chrona/presentation/renderers/v05_svg.py`; keep PNG on the pinned resvg
path. Extend `src/chrona/presentation/scene/contrast_policy.py`,
`perceptibility.py`, and their public checker mappings so both substrate and
ink reach each gate. Update `src/chrona/usecases/render_review.py` only at the
closure-to-Layout-to-Scene seam.

**Migration:** Theme v0.11 and derived v0.12 remain valid and unchanged; the
new contracts are v0.13/v0.14. Scene v0.6 remains unchanged; v0.7 carries the
new completed tile, angle, density, origin, and clip. Context schema fields
do not change; closure resolution accepts and pins catalog v0.4. Pattern
resolution rejects unsupported role/property pairs before Layout and reports
`E_THEME_ASSET_REFERENCE` with exact Theme JSON pointer and `set:name`; add
the code to `tools/diagnostic_inventory.py` output.
ScenePaint.fill carries opaque substrate and ScenePaint.stroke opaque ink;
PatternGeometry carries no paint or catalogue lookup. Mark contrast checks
substrate-to-host and ink-to-substrate/host at 3.0:1; decoration checks the
same pairwise minimum at 1.10:1. SVG and PNG derive from the same completed
Scene value. An adapter may serialize periodic repetition, but cannot change
tile, angle, origin, clip, or color.

**Focused checks:**

- `$CHRONA_PY -m pytest tests/unit/chrona/presentation/model/test_theme_tokens.py tests/unit/chrona/presentation/model/test_theme_inheritance.py tests/unit/chrona/presentation/model/test_presentation_closure.py tests/unit/chrona/presentation/model/test_draft_closure.py`
- `$CHRONA_PY -m pytest tests/unit/chrona/presentation/layout/test_icon_geometry.py tests/unit/chrona/presentation/scene/test_contrast_policy.py tests/unit/chrona/presentation/scene/test_perceptibility.py tests/unit/chrona/presentation/renderers/test_icon_svg.py tests/unit/chrona/presentation/renderers/test_v05_svg.py`
- Add `tests/unit/chrona/presentation/layout/test_pattern_placement.py` and
  `tests/unit/chrona/presentation/scene/test_pattern_geometry.py` for
  normalized tile-to-Layout placement and Scene projection.
- `$CHRONA_PY -m pytest tests/unit/chrona/presentation/scene/test_capabilities.py tests/unit/chrona/presentation/model/test_semantic_registry_contrast.py tests/unit/chrona/usecases/test_render_review.py`
- Add `tests/unit/chrona/presentation/layout/test_mark_geometry.py` and
  focused catalog-glyph mark-fit coverage in the lane-facet/composition tests;
  cover every allowlisted role and forbidden
  role, wrong-kind/missing-reference pointer, Theme inheritance, Scene v0.7
  schema, exact SVG `<pattern>` values, and resvg-decoded PNG checks.
- Run conformance, schema annotations/references, import-direction and module
  reachability checks for the added Theme/Scene dependencies.

**Generated/review evidence:** serialized v0.7 Scene fixture with complete
paint/tile/angle/density/origin/clip; matching SVG with stable pattern units
and transform; PNG decoded from the same SVG; pairwise contrast results and
perceptibility findings for mark and decoration fixtures; byte comparison
showing adapters did not resolve assets or Theme tokens.

**Publication boundary:** one Theme/Scene ownership commit after Slice 1.
Review the schema and Scene delta together; do not publish Theme declarations
without their closure, completed Scene, adapter, and paint-gate consumers.

## Slice 3 — builtin catalogue, preset library v0.2, and closure

**Owned files:** add `schemas/preset-library-v0.2.schema.yaml` and update
schema inventory/readme; update `src/chrona/usecases/preset_library.py`,
`src/chrona/resources/__init__.py` for builtin member-root resolution,
`src/chrona/resources/presets/library.yaml`, and one generic bundle, proposed
`src/chrona/resources/presets/bundles/executive-light/` (Theme, optional
detail, and library entry). Ship the starter catalogue, `.NOTICE`, and
provenance manifest under `src/chrona/resources/icons/`; update resource
packaging and exact-reference checks. Update `chrona preset copy` generation
to place declared catalogues/notices under `catalogs/` and preserve their
references in the generated `presentation-preset/v0.1`. Confirm
`src/chrona/presentation/model/closure.py`,
`src/chrona/usecases/materialize.py`, and the `render --preset` path close the
copied catalogue exactly; no directory scan or new flags. Add/extend
`tests/integration/test_project_generic_presets.py`,
`tests/integration/test_public_preset_evidence.py`,
`tests/integration/test_packaged_resources.py`, and
`tests/integration/test_materialize_example.py`.

**Migration:** builtin preset library v0.1→v0.2 adds optional catalogue
members; presentation-preset v0.1 stays as-is because it already declares
`iconCatalogs` and `detailProfile`. Copy retains the current nonempty-output
refusal and adds exact member byte/identity/notice closure. The candidate
executive-light bundle must remain project-generic and use its existing
review-detail profile for legend content; do not copy Controller-Z or
HALCYON-specific facts into the builtin resource.

**Focused checks:**

- `$CHRONA_PY -m pytest tests/integration/test_project_generic_presets.py tests/integration/test_public_preset_evidence.py tests/integration/test_packaged_resources.py`
- `$CHRONA_PY -m pytest tests/integration/test_materialize_example.py tests/cli/test_cli.py::test_cli_builtin_preset_copy_rejects_unknown_or_nonempty_output tests/cli/test_cli.py::test_cli_render_preset_by_name_is_byte_identical_to_copy_then_path`
- Copy the selected preset into an empty temporary directory; check exact
  catalogue, notice, and `preset.yaml` references. Render a fresh starter and
  the declared generic fixture through `--preset` without asset flags; assert
  glyph, pattern, and legend are present in completed Scene and SVG.
- Check missing member, corrupt identity, absent notice, and nonempty-output
  failures; verify no unrelated builtin preset/member changed.

**Generated/review evidence:** starter catalogue normalized source, output,
identity manifest and notice; copied directory byte-identity report; Scene,
SVG, and PNG from `chrona preset copy` followed by `chrona render --preset`;
catalogue and bundle inventory showing all requested glyphs and all six
pattern entries: halftone dots, seigaiha, ordered-dither at 12.5%, 25%, and
50%, and dense hatch. Glyph inventory names pin, lantern, hexagon, star, chest,
ticked circle, and diamond.
Inspect actual SVG and decoded PNG together; a Scene-only assertion is not
user-visible acceptance.

**Publication boundary:** builtin distribution and copy/render closure commit.
Do not combine resource provenance or rendered artifact corrections without
rechecking identity and the public materializer diff.

## Slice 4 — issue acceptance and release evidence

**Owned records/artifacts:** update the living work record with exact commits,
commands, changed generated bytes, and evidence links; add one concise
`docs/reviews/current/issue-496-theme-asset-catalogues-acceptance-review-2026-09-28.md`
after implementation and CI. Regenerate public example materializers through
`tools/regenerate_public_examples.py --write` only if a source example/context
was intentionally changed, then require `--check --jobs 4`. Normally these
builtin bundle changes should leave unrelated public SVG/Scene artifacts
byte-identical. Inspect all changed SVG, emitted Scene, and decoded PNG as one
batch; account for each byte change.

**Focused/release checks:** rerun Slices 1–3 tests; run the repository's full
pytest and conformance CI matrix on all three operating systems, wheel/smoke,
and newest-Python public materializer jobs. Locally, use the project virtual
environment and do not duplicate the full suite without a concrete risk. Run
`$CHRONA_PY tools/check_starter_perceptibility.py`,
`$CHRONA_PY tools/presentation_contrast.py --check`,
`$CHRONA_PY tools/regenerate_public_examples.py --check --jobs 4`,
`$CHRONA_PY tools/check_issue_acceptance_reviews.py`,
`$CHRONA_PY tools/schema_inventory.py`,
`$CHRONA_PY tools/validate_schema_references.py`, and packaged-resource
checks on the intended final base. Record every failing CI check and whether it is
introduced by this work before acceptance.

**Publication boundary:** acceptance-review commit follows the three
implementation commits and current CI evidence. Keep #496 open if any literal
criterion is deferred or lacks user-visible proof; do not close it in this
phase.

## Acceptance evidence map

| Literal criterion | Required evidence at release |
|---|---|
| 1. Catalogue holds normalized glyph/pattern entries with license/notice. | v0.4 schema/import positives and rejection matrix; canonical identity; packaged starter catalogue and notice. |
| 2. Theme glyph/pattern, identical SVG/PNG, paint gates. | Theme v0.13/derived v0.14 and Scene v0.7 closure; exact SVG/PNG rendering comparison; contrast/perceptibility checks over opaque substrate/ink channels. |
| 3. Builtin catalogue/detail, copy with notices, render without extra flags. | v0.2 library copy tree byte/identity report; copied preset `iconCatalogs`/`detailProfile`; public CLI render of copied preset with no extra catalog options. |
| 4. Requested starter assets and preset glyph+pattern+legend. | Asset inventory confirms seven glyphs and six patterns; copied generic preset's Scene/SVG/PNG visibly uses glyph/pattern and emits legend. |
| 5. Missing ref reports Theme pointer and `set:name`. | Negative CLI/closure case asserts `E_THEME_ASSET_REFERENCE`, exact Theme pointer, and authored reference before Layout/output. |
