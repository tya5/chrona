# Design Plan — #466 C4 Contrast Closure and Acceptance Evidence

**Issue:** [#466](https://github.com/tya5/chrona/issues/466). **Plan base:** fetched `origin/main` at `7f612e7421f6f123a5fd1f3e5cedb5f2472cb39e` (2026-09-27). **Predecessors:** [candidate placement design](../../design/issue-466-candidate-placement-design-2026-09-26.md), its [architecture review](../../reviews/current/issue-466-candidate-placement-architecture-review-2026-09-26.md), [C2–C4 implementation plan](issue-466-candidate-placement-implementation-plan-2026-09-26.md), and [C3 sequencing correction](issue-466-c3-sequencing-correction-2026-09-27.md). This document plans C4 design/closure; it does not approve a final semantic decision or authorize product implementation.

## Baseline: published, lead, and unverified

### Published on the fetched base

- #466 C2 candidate/source/tail capability is on main (the handoff identifies commits `5b96ee50` and `812d5c77`); View v0.25 carries that capability, while the live View schema is now v0.26. The exact current schemas and resources must be inventoried from this base before implementation planning.
- The published C3 sequencing correction says HALCYON-1 `02-programme-board` is to be re-measured after #467 L3 moves it to lane rows. It records the earlier 26-row plot trial's `tvac-note` failure and forbids widening bounds, dropping obstacle classes, or weakening acceptance to hide the failure.
- The current #467 published handoff still describes its lane work as WIP, over the ≤12 lane limit and needing correction/re-measurement. Therefore “after #467 L3” is a dependency condition, not evidence that the lane geometry or C3 fixture is already available on main. Recheck #467's design, implementation, and published evidence before scheduling C3/C4 against it.
- Specification 07 already defines `annotationContainer` rectangle/balloon/image treatment. For image-backed containers it says the fill binding is the Theme author's representative content-area colour and that contrast and perceptibility consume it as rectangle fill. The [#465 design amendment](../../design/issue-465-image-annotation-container-design-amendment-2026-09-27.md) and [architecture review](../../reviews/current/issue-465-image-annotation-container-architecture-review-2026-09-27.md) establish that ground semantics; C4 should verify the actual implementation and preserve the contract.
- #478 I478-3's published role/property admission review establishes `contrastTreatment` as a finite Theme role property and requires authored Theme closures and Scheme targets to be admitted at load time. Its six-binding migration impact for this C4 work is a read-only audit lead and must be enumerated against current effective Theme/Scheme closures before the migration is fixed.
- Issue #466 remains open. The issue body, rather than handoff summaries, is the authority for the seven literal acceptance criteria copied below.

### Leads to verify, not published conclusions

- The supplied read-only audit reports that `annotation-note-text` should be `STATE_TEXT`, while `annotation-note-box` should be `DECORATION`; it reports neither currently has a `ContrastClass` in `semantic_registry.py`. Confirm the current registry and contrast consumer behavior at the plan base, including what classifications imply for floor treatment and background-ground lookup.
- The audit reports six effective Theme bindings need `contrastTreatment` migration when note text becomes classified. Their exact resource paths, direct-versus-Scheme source, inherited/effective closure, and values are not recorded here; enumerate them before choosing migration details.
- The audit reports that `annotation-note-box` fill is the representative fill used beneath note text even for #465 image outline. Verify that `_ground_under`, Scene projection and perceptibility consume this same declared fill, and that generated SVG remains consistent with the completed Scene paint.

### Unverified at plan time

- Whether the current public main contains a completed #467 L3 and whether `02-programme-board` can now satisfy literal criterion 3 after the lane geometry change.
- Exact C3 resource/view/theme versions and exact six Theme bindings after current-main migrations.
- Actual rendered SVG (and available PNG) evidence for three notes, note text contrast, image-backed ground, crowded rail fallback, and the #449 exhausted-search completion.
- Whether adding these classifications changes any public contrast report or rendered bytes, including non-HALCYON consumers of the note semantic roles.

## Literal issue acceptance criteria

The following seven rows are copied verbatim from the current issue body and remain the closeout ledger. C4 must report each as `met`, `deferred`, or `not met` with direct evidence; a deferred or unverified row leaves #466 open.

1. One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.
2. Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.
3. A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.
4. The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.
5. Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.
6. A Theme can draw the tail and balloon outline. A Theme without it renders as today.
7. The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.

## C4 objective, responsibility boundaries, and decisions to review

C4 completes the acceptance/release audit after the C3 fixture has been validly re-measured. Its contrast-closure slice must make note text participate in the established state-text contrast-floor contract, classify the note box as a decoration for the corpus contrast witness, preserve the #465 representative-fill ground for note text, and migrate every affected effective Theme closure atomically. C4 then inspects actual adapter output and the complete seven-row ledger; it does not change candidate search, obstacle policy, note geometry, or #467 lane allocation.

**Theme decision under review:** classify `annotation-note-text` as `STATE_TEXT` and `annotation-note-box` as `DECORATION`, subject to the full role-family/witness and architecture review. The text class owns state-text contrast-floor participation. The box class supplies a decorative contrast witness and does not make the box itself text. Confirm that this is the intended semantics of the existing `ContrastClass` consumers; do not infer a new contrast policy from the class names alone.

**Theme migration decision under review:** determine a valid `contrastTreatment` for every effective note-text binding under #478 admission, following established state-text policy and current Theme/Scheme precedence. Preserve declaration provenance and pointer diagnostics. Inventory the reported six bindings by exact resource path; do not migrate only the visible HALCYON Theme if shared/preset/derived closures consume the roles.

**Ground contract under review:** keep `annotation-note-box.fill` as the declared representative content-area ground in Scene contrast/perceptibility calculations, including `annotationContainer.outline: image`. C4 must prove how transparent/alpha fill and absent fill are treated by current contracts. Any mismatch between specification, contrast implementation, perceptibility, and emitted paint pauses the slice for a design correction.

**Open decisions/questions before implementation planning is final:**

1. Does `DECORATION` classification of the note box satisfy the corpus witness without falsely asserting contrast for an unpainted or filtered note box? What evidence demonstrates it?
2. Does `STATE_TEXT` introduce any `contrastTreatment` defaults, diagnostics, or floor behavior beyond existing note Theme declarations? What exact treatment values are required by current policy for each of the six bindings?
3. Are note text and box always emitted as a paired container in public output, or can a note-text role render without a note-box ground? If it can, how does current `_ground_under` represent its actual background without fabricating one?
4. For #465 image-backed containers, does the declared representative fill remain the authoritative contrast ground even when artwork pixels differ? Specification 07 says yes; verify consistency across contrast, perceptibility and SVG/PNG evidence without sampling image pixels in an adapter.
5. What is the remeasured #467 L3 public state and the exact C3 slide geometry at the handoff point? If no qualifying C3 evidence exists, C4 acceptance cannot be treated as complete.
6. Which active Theme roots, inherited themes, Scheme bundles, generated diagnostic inventories, and materialized scenes change? What is the minimum atomic migration set that leaves every supported context materializable?

## Whole-architecture review targets

The architecture review must inspect the complete ownership path and adjacent contracts, not just the registry edit:

- **Project/View/Theme:** Specification 02 and 06 source/reference ownership; Specification 07 note-box/text role semantics, `annotationContainer`, representative fill, and `contrastTreatment`; #478 I478-3 role/property admission and exact direct/Scheme diagnostics. Verify no View field or Project meaning is changed by contrast classification.
- **Theme/Scheme closures:** `semantic_registry.py`, role/property consumer capability registry, `theme_tokens.py`, `color_scheme.py`, all six audited effective bindings, preset bundles and derived/pinned resources. Admission and migration must be complete before a Theme closure reaches Layout.
- **Layout:** candidate completion and box/tail placement stay Layout-owned per Specifications 33/44. Contrast closure must not alter measured geometry, chosen candidate, obstacle index, fallback, or route priority.
- **Scene/contrast/perceptibility:** Specifications 08 and 50; `scene/contrast_policy.py` ground selection and floor application; `scene/perceptibility.py`; note text and box Scene roles, `contrastTreatment`, and image-backed declared-fill ground per #465. Confirm a single, renderer-neutral policy with no pixel inspection or adapter repair.
- **Adapters/public artifacts:** SVG and typeset serialization plus PNG derivation. Inspect rendered public output, not only Scene reports. Identify intentional byte changes from text contrast treatment and verify unchanged geometry/route/placement provenance where not explicitly intended.
- **Adjacent designs and release policy:** #465's image container contract, #467's lane dependency/re-measurement, #478 role admission, #449 visible exhaustion, #459 contrast, #446 perceptibility, and Specifications 06/07/08/33/44/50. Record incompatibility/migration only if a public contract actually changes.

## Design and publication slices

1. **Baseline and evidence inventory (this plan):** record fetched `origin/main` SHA, literal issue criteria, current published C2/C3/C4 documents, role/class state, all effective Theme/Scheme bindings, #465 ground path, #467 publication status, and available C3 rendered artifacts. Keep published facts, audit leads, and unverified items separate as above.
2. **Contrast contract decision:** publish an English C4 design/amendment specifying note text/box contrast classes, treatment semantics and required Theme values, note pairing/ground behavior, #465 declared-fill behavior, diagnostic expectations, and no geometry/adapter ownership change. If these semantics alter normative guarantees, update Specification 07 and any directly affected specification; record migration impact and predecessor/successor links.
3. **Whole-architecture review:** publish review of the selected contract across the targets above. Reconcile any disagreement between contrast witness requirements, #478 property admission, #465 ground semantics, or #467 sequencing before implementation planning. No product-code edits in this design phase.
4. **C4 implementation plan:** enumerate exact source/schema/resource/test/evidence owners; six binding migrations; focused tests; generated inventory/report/materializer updates; public SVG/PNG batch; CI gates; rollback/publication boundary; and each literal criterion's required evidence. Keep C3 fixture adoption atomic and dependent on the published #467 L3 result and C3 remeasurement.
5. **C4 implementation and acceptance (future authorized phase):** implement only after design, review, and implementation plan are published. Publish contrast migration as a coherent slice; publish rendered-output and CI/literal-acceptance review separately. Close #466 only if all seven rows are met and every required release gate is green.

## Acceptance evidence required from C4

- Focused checks prove the semantic registry assigns the intended classes and `presentation_contrast` observes both note text and note box in the relevant corpus; tests cover the text floor and decorative witness separately.
- Role-admission and closure tests cover direct Theme declarations, Scheme-inserted targets, base/inherited and derived Theme roots, exact source pointers, and all enumerated migrations.
- Contrast/perceptibility tests demonstrate `annotation-note-box.fill` is the declared representative ground for note text under rectangle, balloon, and image outlines, without renderer-side pixel sampling. Verify alpha/no-fill cases against the approved contract.
- On the post-#467-L3 C3 fixture, regenerated Scene/SVG (and PNG if a public PNG artifact exists) visibly shows all three notes, clear note text, candidate/fallback diagnostics, no forbidden collisions, and no as-of crossing. Inspect the artifact batch directly.
- Public materializers run as one batch; compare Scene and SVG against the exact public base, attribute each byte change, and confirm non-target geometry/search/route outputs remain stable. Run focused tests and repository-planned CI; inspect the actual run and report every failed check.
- The final acceptance review has one row per verbatim criterion above, exact commit and commands, CI/PR links, artifact diffs, architecture findings, and `met`/`deferred`/`not met` plus direct evidence. Scene-only output does not prove visible SVG/PNG acceptance.

**Publication boundary:** publish this plan first. Design, whole-architecture review, and implementation plan are separate public documents before product implementation. Do not push, comment on the issue, edit a reviewer board, or treat an unpushed worktree as published completion. C4 cannot close the issue while C3 or any literal criterion lacks accepted evidence.
