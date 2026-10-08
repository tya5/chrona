<!-- chrona:literal-acceptance/v1 -->

# Release Review — Native Slot Headings

## Literal issue acceptance

### Issue #1100

- Source: [Issue #1100](https://github.com/tya5/chrona/issues/1100).
- Observed: 2026-10-08
- Current design and implementation plan: [Status](https://github.com/tya5/chrona/issues/1100#issuecomment-6041732444).
- Reviewed implementation: [`7dc9fb6e`](https://github.com/tya5/chrona/commit/7dc9fb6eada23e0bb34e69975f6fd8cc027faa1a), including footer/preparation correction `0b9ac866`, on ready base `90c3ef0e`. Release requires the exact-main gate below; its receipt belongs in the current work record.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `block: header-row` centres the caption in the whole axis band; the approved mock puts NOTES on the baseline of the upper axis tier. A tier-aligned variant needs the axis tier geometry (`surface_axis`). | met | [Actual SVG baseline and fallback tests](../../../tests/integration/test_slot_heading_copy.py); [native tier geometry](../../../tests/unit/chrona/presentation/layout/test_surface_axis_tier_geometry.py). | — |
| 2 | A View-level override of the caption copy (today a Context overrides it through a derived Layout Profile `overrides`). | met | [Actual SVG copy, immutable default, node identity and exact-pointer tests](../../../tests/integration/test_slot_heading_copy.py); Spec06 §7.5. | — |
| 3 | Headings on `group-details`, `milestones`, `observations` (and the `title`, `table`, `timeline`, `timeline-axis`, `network` sources, which reject a heading today because other rules own their block). | met | [All eight native sources in actual SVG and validated serialized Scene](../../../tests/integration/test_native_slot_headings.py); [all-source/derived profile admission](../../../tests/unit/chrona/presentation/layout/test_slot_heading_profile.py). Timeline/detail and network PNGs visually inspected. | — |
| 4 | A content-sized slot whose source is empty keeps the caption's block in its measurement though no caption is drawn. | met | [Empty/full summary, consumed notes, empty legend and empty axis SVG comparisons](../../../tests/integration/test_empty_slot_heading.py); [shared detail/axis measurement and completion presence](../../../tests/unit/chrona/presentation/layout/test_slot_heading_placement.py). Empty selected content neither draws nor measures a suppressed caption. | — |

## Programme-level criteria (optional)

### Architecture and verification

- View selects copy; Theme owns typography/paint; Layout closes exact-candidate natural prefix and final geometry; Scene/adapters only project/serialize. Native axis guards remain strict. Primary Scene table-reference closure is unchanged; auxiliary observation purposes retain their own attribution and state paints (Specs28/08).
- Candidate finite/auto renders and width-change lane preflight: [integration](../../../tests/integration/test_surface_candidate_demand.py), [natural closure](../../../tests/unit/chrona/presentation/layout/test_surface_natural_geometry.py). No fill-expanded measurement or previous-candidate preflight.
- Empty-axis presence uses normalized tiers; title fallback, selected rows/table columns and required network nodes keep their contracts. Empty-axis regression63 passed, with a real nonempty-tier prefix fixture and byte-identical empty-axis SVG.
- Focused evidence: engine/allocation51; axis/natural/allocation66; copy/render13; native SVG/serialized Scene/observations/contrast78; preparation69 plus corrected ownership/source-phase wiring4; updated caller seams13; capped native overflow2; footer integration2; detail/footer11. These sets overlap. Schema equivalence PASS (two optional deltas); float/literal-review/source-only gates PASS; import direction11 packages/37 inward edges; reachability193/no orphans. Full pytest is CI-owned, not claimed locally.
- Preparation extraction preserves all12 moved definitions by AST comparison; the composer is343 lines. Lane tests retain actual candidate preflight, subtrack and natural-demand assertions. Native Japanese panels retain presence/containment/non-overlap; [narrow native CJK test](../../../tests/unit/chrona/presentation/layout/test_detail_caption_viewports.py) proves wrapping and raw-source preservation.
- CLI timeline/network PNGs and native captions were visually read. Six synthetic unheaded bundled/default-or-explicit-lane SVG/Scene/slot comparisons against `bb5cdc8a` were exact; this is not a corpus-wide default-byte-identity claim. Observation host overflow uses the shared geometry tolerance without altering enclosing bounds.
- Independent non-monotone extent defect remains [#1214](https://github.com/tya5/chrona/issues/1214), with experimental code and unsuppressed repros publicly preserved. No generic least-height repair or waiver is claimed here.

### Public artifact review

- [PR #1218](https://github.com/tya5/chrona/pull/1218), [shared snapshot run37704804324](https://github.com/tya5/chrona/actions/runs/37704804324), artifact11519432121 on head7dc9fb6e/base90c3ef0e: all143 before blobs match the exact base, with equal before/after/manifest pathsets. No new/retired paths;41 Scene/SVG pairs and4 reports change;26 pairs remain byte-identical. Snapshot tar SHA256 `275b677da3a03fca418d08016bd05227298629c03c2ea5cd639b52182a819030`.
- Per-output counts are disclosed on the PR:451 observation texts added,3 plot labels suppressed with explicit `W_LAYOUT_LABEL_SUPPRESSED`/`I_LAYOUT_PLOT_LABELS_SUPPRESSED` records (table copies remain),1025 primitives modified. These are intended completed-content/geometry effects, not a default-byte-identity claim.
- Shared perceptibility evaluator over all67 public Scenes: **0 errors,7294 observations**. Final annotations SVG SHA256 `62f2b024be91860d6a2ac105e24486572a772197f173a196025530736f8a00a4` matches the actual rendered/visually inspected correction. Real SVG/PNG evidence read as a batch: annotations, annotation-artwork, annotation-kinds, viewer-fit, slot-heading before/after, capabilities, Japanese executive and Orion gates. Native detail attribution is visible.
- Implementation-head CI run37704804324 passes all three pytest shards, conformance, MCP-floor and newest-Python reproduction. Final review-head PR readiness and exact-main release remain the publication conditions below.
- Diagnostic deltas:41 truthful footer track overflows and3+3 plot-label suppression records added;40 group-detail,3 milestone and1 legend overflow records removed. Footer Flow intrinsic allocation is separately tracked in [#1219](https://github.com/tya5/chrona/issues/1219); declared visible overflow is not hidden or absorbed into corpus YAML. Integer group-header counting was made explicit as boolean accumulation after the first CI's `E_LAYOUT_FLOAT_SUM_UNCLASSIFIED`; the unchanged checker and25 focused tests pass.
- Earlier failures are dispositioned in the work record: integer counting made explicit; four annotation/note intersections/occlusions corrected by the completed footer union; stale mocks and source semantics updated without dropping geometry assertions; ownership gates restored. Six footer cases cover wrapped/unwrapped, growth/no-growth, disjoint and notes-only inline overlap. Final notes end935.2; annotations start951.2: the declared16px gap. No corpus changes or evaluator exemptions.
- Native overflow uses a genuinely capped row and retains ellipsis/suppression assertions. Flow's ignored leaf inline caps and intrinsic allocation remain [#1219](https://github.com/tya5/chrona/issues/1219#issuecomment-6049196576); no generic parent-flow repair or warning waiver is claimed.

## Publication requirements

Before release acceptance and closure, verify all final-head PR checks, snapshot identity across this review-only publication, and the exact review-containing main's three-OS pytest/conformance/wheel-smoke, MCP and newest-Python materializers. Record exact commit/run receipts in the linked current work record. No generated or `examples/**` edits are authored.
