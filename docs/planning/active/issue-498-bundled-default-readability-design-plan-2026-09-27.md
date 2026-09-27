# Design Plan — Bundled Default Readability Regression (#498)

**Issue:** [#498](https://github.com/tya5/chrona/issues/498).\
**Published baseline:** `90306256219a1888fb674bf8677d28739eca244d` on GitHub `main`.\
**Status:** design planning; owner direction received in [the #498 decision comment](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).\
**Successor documents:** selected design in `docs/design/issue-498-bundled-default-readability-design-2026-09-27.md`, whole-architecture review in `docs/reviews/current/issue-498-bundled-default-readability-architecture-review-2026-09-27.md`, and implementation plan in `docs/planning/active/issue-498-bundled-default-readability-implementation-plan-2026-09-27.md`.

## Published baseline

The issue reports that a bare `chrona render` of HALCYON-1 lost plot row guides and member names after commit `18eba245` repointed the bundled default to Editorial. It also reports that the readable-defaults integration test was changed to render `examples/halcyon-1/views/default-draft.yaml` with explicitly selected resources. Its cited observation base is `bd1463c8`; this plan rechecks the behavior against the newer published baseline above.

The owner's comment on 2026-09-27 adds a fourth criterion and selects a YAML-level direction. It says the default should keep Editorial's look while adding readability; the `editorial` catalogue entry and `13-gallery-editorial` remain reference-faithful. The comment's exact implementation intent and evidence requirements are transcribed below rather than inferred from the earlier issue body.

At the published baseline:

- `src/chrona/resources/presets/default.yaml` selects the Editorial View, Theme, Scheme, Layout, and Detail Profile.
- `src/chrona/resources/presets/bundles/editorial/view.yaml` declares `visibility.labels.placement: table` and `backgroundDecoration.rows: none`.
- `tests/integration/test_readable_defaults.py::test_default_draft_guides_every_bar_across_the_plot_and_names_it_at_its_end` explicitly supplies the separate `default-draft` View, briefing Theme and Layout, and mission-light Scheme. Its docstring says this avoids testing the bundled Editorial default, citing #425's Editorial reference principle: “only the columns carry ground; the rows carry none.”
- `tests/integration/test_project_generic_presets.py::test_each_preset_renders_halcyon_and_the_starter` renders each named catalogue preset and an initialized starter. It does not check readability when the bundled default is selected with no presentation flags.
- The #483 acceptance review records the readable `default-draft` criterion as narrowed and hands the row-local label issue to #488. The #488 review records that visible labels now stay within their own row or are reported suppressed, with actual counts and generated-slide evidence.
- At issue observation base `bd1463c8`, the issue records 27 HALCYON-1 rows over a 1768 px plot, zero `row-band:*` primitives, and zero member labels in the plot. The owner comment retains this as the regression baseline; current-main counts still require reproduction.

## Literal #498 acceptance criteria

The issue's three original criteria and the owner's additional fourth criterion are copied verbatim:

1. “A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed.”
2. “The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test.”
3. “The same holds for the `chrona init` starter.”
4. “The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis.”

## Published facts, design points to verify, and unverified points

### Published facts

- The current bundled default resolves to Editorial, whose View intentionally has no row stripes and places names in the table.
- The existing readable-defaults test exercises the pinned `default-draft` configuration, not the bundled default.
- #425's Editorial reference uses a table-ground/no-row-ground visual principle. The #483/#488 readable-defaults line uses row guides and names in each row. These aims conflict if the bundled default must reproduce Editorial's reference verbatim.
- The reported first-time-user regression affects both bare render selection and the default preset consumed by `chrona init` starter rendering.
- Issue #498 is open. The owner has selected a readable Editorial-look bundled default, with a separate reference-faithful `editorial` catalogue entry and `13-gallery-editorial` slide.
- The owner specifies View labels `placement: both`, `side: end`, and fallback `[end, start, suppress]`; plot names use small navy type while table names remain. The owner also selects `rows: alternate` with a very faint warm tint from the Editorial palette. The tint must remain just perceptible, pass `starter-perceptibility`, and remain well below the columns' ground.
- The owner says a hairline row rule is not expressible in View v0.26 and is a B-depth follow-up only if the alternating tint proves too heavy. The selected change is C-depth YAML plus the test correction.

### Design points to verify

- Determine the exact default View/variant resource identity and package mirror topology that separates the readable default from the reference-faithful `editorial` bundle and gallery slide.
- Confirm `placement: both`, the label fallback, row-locality, suppression diagnostics, warm row tint and starter-perceptibility can all be expressed with the current View/Theme contract and existing Layout behavior.
- The owner expects a C-depth YAML/resource change plus test correction. Verify this scope against current schemas, CLI/init resolution, and #466/#467 boundaries before carrying it into the selected design. If product-code or Layout change is necessary, return to design review rather than silently expanding implementation.

### Unverified points

- Reproduce the reported missing guides and plot names at `90306256` using the public bare-render invocation, inspecting both Scene and rendered SVG.
- Establish whether `chrona init` embeds or otherwise selects this same bundled default, then render the generated starter without presentation overrides and inspect Scene/SVG.
- Confirm the current HALCYON-1 project size, row count, guide count, label count, and suppression diagnostics on the published baseline; the issue's 27-row/1768-pixel values describe its observation commit and are not assumed current.
- Determine whether the selected default can meet all per-row label dispositions with current Layout behavior. #488 evidence for an explicitly selected View is relevant precedent but does not itself prove bundled-default behavior.
- Check whether a default resource change affects additional package mirrors, example Contexts, public materializers, or generated artifacts beyond those already identified.

## Selected owner direction and design review questions

The owner decision resolves the default-versus-catalogue choice: keep the Editorial look as the bundled default and add readability within that look. Do not revert to an older plain draft. The owner selected:

- a default-owned View or Editorial variant, separate from the `editorial` catalogue View and `13-gallery-editorial` reference reproduction;
- `labels.placement: both`, `side: end`, and fallback `[end, start, suppress]`, with plot names in small navy type while the table keeps the names;
- alternating row guides using a very faint warm tint from the Editorial paper palette. It must be perceptible, pass `starter-perceptibility`, and sit well below the table columns' ground;
- a hairline row rule only as a B-depth successor if the stripe is too heavy, since View v0.26 has only `rows: none | alternate`;
- C-depth YAML/resource changes plus the regression-test correction.

The owner also requires regenerated HALCYON-1 and starter evidence, a side-by-side comparison with `13-gallery-editorial` in the acceptance review, and preservation of palette, type, and axis. These are part of the acceptance contract, not optional visual polish.

The selected design and architecture review must answer:

- What exact View identity and package-owned resource set should the readable default use so it cannot mutate the `editorial` catalogue entry or `13-gallery-editorial`?
- How should `labels.placement: both` express the table title plus plot label without duplicate or competing facts, and which label content and typography bindings produce the intended small navy treatment?
- Which warm palette token and opacity make alternate row tint just perceptible, pass `starter-perceptibility`, and remain well below the table columns' ground? What rendered comparison establishes this?
- Does current Layout honor the end→start→suppress ladder within each row for this separate View, and does it emit a corresponding diagnostic for every suppressed name?
- What exact resources do bare `chrona render` and `chrona init` starter use? How will the new View be packaged, mirrored, selected, and tested without changing the named Editorial preset?
- Does the hairline guide remain deferred unless the selected warm tint looks too heavy? If evidence requires it, record it as a B-depth successor rather than adding schema or Layout work to this C-depth slice.
- How do #483's default-draft criterion and #488's row-containment rule apply to a bundled preset and starter without claiming a pinned-resource test as proof?
- What is the intended scope of default selection for projects, explicit named presets, catalogue entry copies, and immutable rendering Contexts? Which must remain unchanged?
- Can the correction proceed independently of #466/#467's in-progress Layout work? Recheck their current published state at design time; do not rely on an unpublished branch or silently absorb lane-mode behavior into this issue.
- Which specifications or ADRs are normative for the default preset and Editorial reference? Update them only if the selected behavior changes a compatibility promise, identity rule, or published visual contract.

## Dependencies and boundaries

- **Owner choice:** received in [the decision comment](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933); the selected direction is transcribed above. Exact resource identity and visual tuning remain design decisions.
- **#483:** predecessor for the readable default-draft behavior and acceptance evidence. Its existing criterion was narrowed; #498 concerns whether those properties hold for the user-visible bundled default.
- **#488:** predecessor for row-local member labels and explicit suppression evidence. The design must verify this behavior through the selected bundled preset and public adapter output.
- **#425 / #429 / #383:** Editorial reference and catalogue/default intent. Review the relevant design and review documents before treating the Editorial appearance as either immutable or freely changeable.
- **#466 / #467:** adjacent in-progress Layout work. The baseline design must establish whether the regression fix is resource/test work or needs a Layout capability. Do not couple the minimal correction to lane rows or make claims based on unmerged work.

## Acceptance evidence and test direction

The implementation plan should include focused cases for:

- the public `chrona render <HALCYON project>` invocation with no `--view`, `--theme`, `--layout`, or `--scheme`, exercising the bundled default;
- row-guide coverage across the timeline for every selected bar, with Scene geometry checked structurally;
- each selected member name either visibly placed at its bar's end or start within its own row, or represented by the corresponding suppression diagnostic;
- the same checks for a project created by `chrona init`, rendered without presentation overrides;
- a retained pinned `default-draft` test if useful, clearly supplemental to (not a substitute for) bundled-default coverage;
- the `starter-perceptibility` check against the faint warm row tint;
- catalogue behavior and Editorial reference identity under the selected owner decision;
- regenerated default Scene/SVG and suitable image captures for HALCYON-1 and the initialized starter, compared side by side with `13-gallery-editorial` in the acceptance review. Inspect that the default retains Editorial's palette, type, and axis while the catalogue slide remains reference-faithful.

Inspect actual SVG output as well as Scene data because acceptance is user-visible. Compare the before/after Scene and SVG batches for HALCYON-1 and the initialized starter; review the relevant rendered images at readable scale, including the side-by-side `13-gallery-editorial` comparison. Record any intentional changes by primitive/resource, confirm no unrelated public artifacts changed, and run the repository's public materializer/conformance and planned CI evidence when the implementation plan defines those gates.

## Planned design and publication slices

| Slice | Work | Gate and evidence |
| --- | --- | --- |
| P0 — baseline and decision | Reproduce current bare render and starter behavior at published `main`; inspect #498 and predecessor issue/design/review records; carry the received owner choice forward. | Record observed values and exact invocations; keep all four literal criteria intact; no product edits. |
| D1 — selected design | Define separate default View identity/resource ownership, warm row tint, both-location label behavior, init/render resolution, migration and compatibility, diagnostics, Layout responsibilities, and any normative-document updates. | Publish an English #498 design document linked to this plan and predecessor records; demonstrate C-depth YAML scope is sufficient or explicitly amend it. |
| D2 — architecture review | Check the selected design against #425 Editorial reference, #483/#488 readable defaults, preset/catalogue architecture, CLI/init boundaries, Layout/Scene/adapter ownership, and current #466/#467 status. | Publish whole-architecture review with resolved choices, risks, and remaining questions. |
| P1 — implementation plan | Name exact owned files/resources, test and public-materializer changes, generated evidence, migration, focused verification, and serial publication boundaries. | Publish implementation plan only after design and review are complete. |
| I1 — implementation and acceptance | Implement the approved smallest slice, regenerate affected public artifacts, inspect Scene and actual SVG/image evidence, and complete an acceptance review row for every literal criterion. | Keep #498 open until all four criteria have direct evidence, including the side-by-side `13-gallery-editorial` comparison, and required CI/public-render gates pass. |

This document records the owner's selected direction but remains a design plan. It does not approve product changes or claim any acceptance criterion met.

## Predecessor documents

- [#483 readable-defaults design plan](issue-483-readable-defaults-design-plan-2026-09-26.md), [design](../../design/issue-483-readable-defaults-design-2026-09-26.md), [architecture review](../../reviews/current/issue-483-readable-defaults-architecture-review-2026-09-26.md), and [acceptance review](../../reviews/current/issue-483-readable-defaults-acceptance-review-2026-09-26.md).
- [#488 row-local member-label design](../../design/issue-488-member-label-row-band-design-2026-09-27.md), [implementation plan](issue-488-member-label-row-band-implementation-plan-2026-09-27.md), [architecture review](../../reviews/current/issue-488-member-label-row-band-architecture-review-2026-09-27.md), and [acceptance review](../../reviews/current/issue-488-member-label-row-band-acceptance-review-2026-09-27.md).
- [#425 Editorial reference issue](https://github.com/tya5/chrona/issues/425), and [#429/#383 preset catalogue design](../../design/issue-429-383-preset-catalogue-design-2026-09-27.md), [design plan](issue-429-383-preset-catalogue-design-plan-2026-09-27.md), and [architecture review](../../reviews/current/issue-429-383-preset-catalogue-architecture-review-2026-09-27.md).
- [#467 lane-row implementation plan](issue-467-collision-aware-lane-rows-implementation-plan-2026-09-26.md) and [prerequisite recheck](../../reviews/current/issue-467-lane-rows-prerequisite-recheck-2026-09-26.md), plus [#466 shared-obstacle prerequisite plan](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md), for current dependency boundaries.
