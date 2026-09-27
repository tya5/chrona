# Architecture Review — #466 C4 Note Contrast Closure

**Design:** [C4 note contrast correction](../../design/issue-466-c4-contrast-closure-correction-2026-09-27.md). **Plan:** [C4 design plan](../../planning/active/issue-466-c4-contrast-closure-design-plan-2026-09-27.md). **Baseline:** product behavior audited at `7f612e7421f6f123a5fd1f3e5cedb5f2472cb39e`; subsequent `main` commits through `cb31af5b` are documentation-only, including the plan at `b7447aad`. **Decision:** approve the selected role classes and migration for implementation planning subject to the gates below. No product implementation or C4 acceptance is approved by this review.

## Whole-architecture consistency

| Authority / layer | Review finding |
| --- | --- |
| Issue #466 and C3 dependency | The current issue body has seven literal acceptance rows and is open. Its latest comments record C3's prior `tvac-note` overflow/occlusion, stale `12-glyph-gates.yaml` base identity, missing regenerated evidence, and the required #467 lane move before remeasurement. C4 design cannot turn those into accepted evidence. The C4 plan correctly keeps rows 3–4 and final visible acceptance conditional on published #467 L3 and a valid remeasurement. |
| Project / View, Specs 02 and 06 | Note content and annotation references remain source/View facts. Contrast classification changes neither source identity nor View selection, candidate order, or Project meaning. The exact seven issue criteria remain the release ledger. |
| Theme / Scheme, Spec 07 and #478 | Six authored Theme roots contain note-text and note-box declarations. All resolve note text fill via Scheme color targets. `resolve_theme` already checks `contrastTreatment` and the numeric state-text floor against the resolved Scheme surface for every role returned by `contrast_bindings(STATE_TEXT)`; adding the note text semantic class activates this existing path, so the six note-text declarations need `required` and do not need a second floor algorithm. Treatment is not a Scheme property. #478's capability registry currently admits `contrastTreatment` only for four existing state-text roles, while the annotation text family has text paint only. The semantic change is inadmissible until `annotation-note-text` explicitly gains that capability; this is a required same-slice change, not an optional follow-up. Direct pointer provenance remains `/body/roles/annotation-note-text/contrastTreatment`. |
| Semantic registry and Scene contrast | `annotation-note-text` and `annotation-note-box` currently have no contrast classes. Existing consumers implement 4.5/3.0 state-text floors, 1.10 decoration floor, state treatment validation, and a corpus-wide enabled-decoration witness. `required` is the coherent note-text treatment because narrative notes do not encode a deemphasized state. `annotation-note-box` therefore requires at least one emitted public witness and will add contrast-report rows/findings. |
| Layout, Specs 33/44 and #466 candidates | Annotation pairing and box/text paint order already belong to the completed Layout/Scene path. The reviewed change does not touch bounds, obstacle policy, connectors, routing, fallback, or search count. No contrast rule migrates into Layout. |
| Scene ground, Specs 08/46/50, #431/#459 | `_ground_under` chooses the topmost earlier Rect/Symbol with fill at a sample point, supports opaque flat fill or a completed gradient, and rejects host opacity other than 1. A Rect with absent fill is skipped, so generic search can fall through to a lower host or canvas. C4 adds an explicit same-source note-box host check for note text and a Theme closure requirement for effective opaque representative fill; both are new validation behavior. The #465 image contract's declared representative fill remains the ground; raster sampling would violate Scene/adaptor separation. |
| #465 image containers | Specification 07 already says the Theme fill is the representative artwork content-area color and contrast/perceptibility consume it as ordinary rectangle fill. Scene `image` paint does not change the declared ground contract. Image pixels and nine-slice mechanics stay outside contrast analysis. The design makes the finite implementation domain explicit: opaque six-digit completed fill. |
| Adapters / public output | SVG, PNG derivation, and typeset outputs serialize Scene paint. A Scene-only contrast report cannot establish reader-visible output. The implementation acceptance must batch-render and inspect public output and verify that only intended contrast paint/report bytes change; geometry and placement provenance remain stable. |

## Contradictions and resolutions

1. **Admission gap:** semantic classification alone would make `contrastTreatment` required in contrast consumers, but the current #478 role/property registry rejects that property on `annotation-note-text`. The design adds explicit admission and all six declarations atomically. Without that, the selected contract cannot reach Layout.
2. **Non-opaque and absent host paint:** the stated #465 representative-fill rule could be misread as allowing any declared color, including transparent fill or partial opacity. The current kernel cannot composite a translucent container over its underlay, and cannot infer the underlying image's pixel color. For non-opaque hosts, existing `_ground_under` returns unsupported; for absent fill, generic search skips that Rect and can select an unrelated host/canvas. The correction adds effective Theme closure validation (`E_SCHEME_ANNOTATION_NOTE_GROUND`) and same-source Scene host validation (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`) for classified note text. Supporting partial opacity requires a later renderer-neutral composition design, reviewed across contrast and perceptibility before implementation.
3. **Decoration witness versus C3 sequencing:** adding a classified decoration creates a new corpus completeness obligation. A future Scene class definition does not itself prove a visible witness; valid C3 public materialization must emit the note box. The correction preserves this dependency and bars a C4 acceptance claim without that evidence.
4. **Published contract versus private artifacts:** #465's normative Specification 07 already establishes image-ground ownership. The C4 spec edits make the note text-to-box relationship and opacity limitation explicit; they do not authorize product code or broaden image handling.

## Decision and implementation gate

The selected classifications are consistent with existing class consumers and the note roles' existing producer kinds (`label`/`decoration`, emitted as Scene Text/Rect). All six authoring roots use opaque Scheme palette bindings for note text/box colors. The treatment migration is `required` for all six note-text role declarations. The existing Theme closure implementation will enforce the note text's required 4.5:1 treatment as soon as it is classified. The implementation plan must include:

- capability admission for `annotation-note-text` and exact-pointer closure coverage;
- six Theme declarations with effective inheritance/Scheme closure and migration evidence;
- separate state-text floor and box decoration-witness checks;
- paired note-box ground checks for rectangle, balloon, and image outline; Theme effective-role opacity/fill validation; and unsupported-ground failures for absent/unpaired host cases;
- report and public Scene/SVG/PNG batch inspection, with paint-only intent and stable geometry/placement provenance;
- C3 fixture adoption only after published #467 L3 and valid all-three-note remeasurement;
- every literal #466 acceptance row with a `met`, `deferred`, or `not met` disposition in the later acceptance review.

The normative edits are in Specifications 07 and 08. No unresolved architecture conflict remains for this selected opaque-fill contract. Partial-transparency support remains expressly outside this design and cannot be implemented by a local contrast special case.

## Read-only contrast probe

An in-memory probe dynamically assigned the proposed classes, injected
`contrastTreatment: required` into committed note-text Scene primitives, and
ran the current Scene evaluator and corpus report without modifying files.
The focused committed controller-z `annotations.scene.json` had one box/text
pair: box contrast was 6.219:1 over canvas; note text was 14.191:1 over
`annotation-box:performance-note` fill `#EAF0F8`. HALCYON-1
`15-gallery-image-notes.scene.json` had three box/text pairs. Box minimum was
1.435:1 (above 1.10) over the declared group host; text was 13.973:1 (above
4.5) over its paired note box `#16213A`. The note-text Scene evaluator selected
the note-box primitive as ground in all four sampled text findings. With note
text treatment injected across the committed corpus, the report had no
corpus-witness error: `annotation-note-box` was enabled in two scenes with four
primitives, and both proposed roles had zero floor errors. This proves current
committed witness presence and these sampled ratios only; it does not prove the
future C3 fixture, a missing-fill rejection (current generic search falls
through), rendered SVG/PNG appearance, or the new paired-host guard. Those
remain implementation/acceptance evidence.
