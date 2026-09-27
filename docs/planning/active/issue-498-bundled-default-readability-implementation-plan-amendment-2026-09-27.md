# Implementation Plan Amendment — Bundled Default Readability (#498)

**Status:** implementation amendment; its product slice begins only after the linked design correction and architecture review are published.
**Issue and owner decision:** [#498](https://github.com/tya5/chrona/issues/498), [owner comment](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).
**Original design plan:** [design plan](issue-498-bundled-default-readability-design-plan-2026-09-27.md).
**Selected design:** [original design](../../design/issue-498-bundled-default-readability-design-2026-09-27.md).
**Design correction:** [title and variance separation](../../design/issue-498-bundled-default-readability-design-correction-2026-09-27.md).
**Original architecture review:** [whole-architecture review](../../reviews/current/issue-498-bundled-default-readability-architecture-review-2026-09-27.md).
**Review amendment:** [correction review](../../reviews/current/issue-498-bundled-default-readability-architecture-review-amendment-2026-09-27.md).
**Original implementation plan:** [implementation plan](issue-498-bundled-default-readability-implementation-plan-2026-09-27.md).
**Successor:** #498 implementation and acceptance review, to be drafted after product slices and release evidence.

## Amendment scope

This amendment clarifies the approved label contract and the evidence gates for I1. Once the linked design correction and review are published, the original implementation plan and this amendment together authorize only their specified product slices and their required phase publications. This supersedes the original plan's final sentence saying it authorizes no commit or push; that sentence applied while the plan was still a proposal and cannot bar the planned implementation. It does not authorize early issue closure. Keep the original paths and publication boundaries except where this document adds a verification requirement.

The default-owned View uses `labels.placement: both`, `labels.content: [title]`, `side: end`, `fallback: [end, start, suppress]`, and `backgroundDecoration.rows: alternate`. Layout continues to emit separate finish-variance labels for combined rows with known `finish_delta`. Those labels keep their current semantic color roles, placement candidates, and overflow behavior. They are independent supplemental content, not member names and not member-name suppression dispositions. Do not append `finishDelta` to member-label content or add a local special case to hide variance labels.

## Literal issue acceptance criteria

These criteria remain verbatim and unchanged:

1. “A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed.”
2. “The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test.”
3. “The same holds for the `chrona init` starter.”
4. “The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis.”

The variance tests below do not replace or weaken any literal criterion. A missing name is accepted only through its corresponding suppression diagnostic and absence of a hidden text primitive.

## Amended I1 gates

### Bundled-default and starter regression coverage

In `tests/integration/test_readable_defaults.py`, exercise the public bare CLI render for HALCYON-1 without presentation resource flags, and render a clean project produced by `chrona init` the same way. Keep any pinned `default-draft` check supplemental and clearly named.

For both output sets, assert from Scene data and actual SVG that:

- the selected rows receive continuous visual guidance through the timeline end: alternate-band edges guide both painted and neighboring unpainted rows;
- every selected bar's member name is either a visible `member-label` anchored at that bar's end or start and contained in its own row, or has its own `W_LAYOUT_LABEL_SUPPRESSED:member-label:<row>:<object>` diagnostic;
- every suppressed member-name identity has no member-label text primitive in Scene and no corresponding text element in SVG;
- every visible member-name identity has no suppression diagnostic, and the aggregate suppression count agrees with the per-name diagnostics;
- HALCYON's combined rows with known finish delta produce the independent `variance:*` labels expected under the title-only View contract; the starter with no known finish deltas produces none;
- variance output remains distinct from the member-name string and resolves through the existing variance semantic treatment. Do not treat variance labels as satisfying, replacing, or weakening a member-name disposition.

The current fixed HALCYON fixture produced 12 separate variance labels in Candidate A. A focused test may assert the expected identity set/count for that fixture, or derive expected combined items from the loaded project/actual facts and compare identities. Prefer checking semantic IDs and text facts over freezing paint values that the approved row-band tuning may change. Candidate A temporarily suppressed `eps`, `detector`, and `avionics`; tests should validate complete accounting rather than hard-code which names Layout suppresses if only Theme sizing changes.

### Resource identity and row-band Theme

Retain the identity checks from I1: new package View/Theme and HALCYON corpus mirrors are byte-identical; only `default.yaml`'s View and Theme references change; the named Editorial bundle, library identity, corpus resources and slide 13 remain unchanged.

Tune the new default Theme's row-band fill to the owner-selected faint warm Editorial palette tint with a dedicated row-band opacity token. Run `./.venv/bin/python tools/check_starter_perceptibility.py` against the actual intended outputs in the project venv and inspect HALCYON and starter output at useful scale. The read-only A/B images used gray `surfaceRaised` at opacity `1` from the unchanged Editorial Theme and are not evidence that the new tint is acceptable. Require a pass and visually confirm the band is perceptible while well below column ground. If no such tint passes both checks, pause for a design correction; do not add a hairline rule or schema property inside this slice.

### Verification and publication sequence

1. **I1 — resources and regression gates:** implement only new default-owned View/Theme resources, exact package/corpus mirrors, default manifest View/Theme selection, and focused tests above. Run resource/schema validation, focused tests, real bundled-default/starter renders, SVG inspection, identity checks, and the candidate-Theme starter-perceptibility gate. Keep the named Editorial and slide 13 byte-stable.
2. **I2 — visual evidence:** regenerate final bare HALCYON and initialized-starter Scene/SVG/PNG evidence only after tint and all I1 checks pass. Inspect at useful scale and compare side by side with `13-gallery-editorial`; record palette/type/axis and row-ground comparisons. Do not publish the exploratory `/tmp` renders as acceptance artifacts.
3. **I3 — materializers and release gate:** run the public-materializer check and planned three-OS CI matrix. Classify all failures and compare generated bytes; use a separate artifact publication if declared public outputs need updates.
4. **I4 — acceptance review:** record direct evidence for every literal criterion, exact implementation and evidence commits, perceptibility result, candidate output counts, SVG and image inspection, comparison with slide 13, materializer and CI results. Keep #498 open if any criterion or required release evidence remains incomplete.

## I1 output table to complete during implementation

Record this matrix in the implementation/acceptance review; Candidate A figures are design feasibility, not product acceptance:

| Output | Selected bars/rows | Band geometry | Visible member labels | Suppressed identities | Separate variance labels | SVG match |
|---|---:|---|---:|---|---:|---|
| Bundled default, HALCYON-1 | To verify | To verify | To verify | To verify | Expected independent labels; verify identities | To verify |
| `chrona init` starter | To verify | To verify | To verify | To verify | None expected for starter fixture; verify | To verify |

The final evidence directory and acceptance review remain as specified by the original plan. Publish each approved product and review unit through the repository's serial pre-push checks; do not update or close #498 until the literal acceptance and CI gates are met.
