# Implementation Plan — Bundled Default Readability (#498)

**Status:** proposed implementation plan; no product changes are authorized until this plan is published and reviewed.
**Design baseline:** `49c8dbe1917208a41e6cf8cb865f18371dc096be` (published selected design and architecture review).
**Issue:** [#498](https://github.com/tya5/chrona/issues/498); [owner decision](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).
**Predecessors:** [design plan](issue-498-bundled-default-readability-design-plan-2026-09-27.md), [selected design](../../design/issue-498-bundled-default-readability-design-2026-09-27.md), [architecture review](../../reviews/current/issue-498-bundled-default-readability-architecture-review-2026-09-27.md).
**Successor:** implementation and acceptance review in `docs/reviews/current/issue-498-bundled-default-readability-acceptance-review-2026-09-27.md`.

## Baseline and constraints

The selected design at the baseline commit gives the bundled default its own Editorial-derived View and Theme, selected by `src/chrona/resources/presets/default.yaml`. It reuses the Editorial Scheme, Layout, and Detail Profile. New package resources are mirrored byte-for-byte in the HALCYON corpus. The named `editorial` catalogue bundle, its library identity, and `13-gallery-editorial` remain reference-faithful and unchanged.

The change is limited to C-depth YAML/resource selection and regression-test correction, plus committed rendered evidence. No schema, Layout, Scene, renderer, CLI, or catalogue behavior change is planned. View declares `placement: both`, `side: end`, fallback `[end, start, suppress]`, and `rows: alternate`; Theme owns the very faint warm row-band fill/opacity. Layout owns row and label geometry and suppression diagnostics. Scene carries completed output; adapters serialize it.

At implementation start, fetch and record the current published `main` SHA and verify that the selected design/review commits are reachable from it. Recheck the published #466/#467 status and relevant merge commits. This plan does not depend on WIP #467 or any unmerged Layout behavior; use only published current-main behavior and the #488 row-local placement contract. The design's trial opacity `0.12` and its baseline counts are feasibility evidence, not acceptance values.

## Literal acceptance criteria

The following four criteria are copied verbatim from the issue body and owner comment:

1. “A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed.”
2. “The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test.”
3. “The same holds for the `chrona init` starter.”
4. “The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis.”

All four must receive an explicit `met`, `deferred`, or `not met` row and direct artifact/test/CI evidence in the successor review. Any deferred row keeps #498 open absent an explicitly approved successor disposition.

## Owned paths and expected changes

Product/resource/test ownership for the implementation slices:

- `src/chrona/resources/presets/bundles/editorial-readable-default/view.yaml` — new default-only View.
- `src/chrona/resources/presets/bundles/editorial-readable-default/theme.yaml` — new Editorial-derived Theme with row-band token binding and tuned opacity.
- `examples/halcyon-1/views/editorial-readable-default.yaml` and `examples/halcyon-1/themes/editorial-readable-default.yaml` — exact byte mirrors of the package resources.
- `src/chrona/resources/presets/default.yaml` — switch only View and Theme references; retain default preset identity, Editorial Scheme/Layout/Detail references, and compatible-scheme declaration.
- `tests/integration/test_readable_defaults.py` — replace the misleading pinned-only default proof with bundled-default coverage. Retain the pinned `default-draft` assertion as a separately named supplemental test if useful. Add checks for continuous alternate row coverage to plot end, per-visible-label row containment and bar-end/start anchoring, complete suppression accounting, and absence of hidden primitives for suppressed labels.
- `tests/integration/test_packaged_resources.py` or `tests/integration/test_public_preset_evidence.py` — assert the two new package/corpus resource pairs are byte-identical; assert the default manifest selects the new pair and that the named Editorial bundle/library identity still references the original Editorial resources.
- `docs/research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/` — committed default render evidence for HALCYON-1 and an initialized starter (Scene JSON, SVG, and PNG captures for each), plus a comparison board/capture pairing each default with `examples/halcyon-1/generated/13-gallery-editorial.svg` (or its PNG capture). Keep this evidence clearly marked as issue evidence; do not add it as a corpus slide or modify the gallery source/context.
- `docs/reviews/current/issue-498-bundled-default-readability-acceptance-review-2026-09-27.md` — acceptance record, exact base/implementation commit, commands, artifact byte-diff summary, side-by-side visual findings, CI links, and four-row literal acceptance table.

Expected intentional product output changes are limited to the bare default and `chrona init` starter outputs. The named `editorial` preset and gallery slide 13 must not change. Do not edit `src/chrona/resources/presets/bundles/editorial/**`, `src/chrona/resources/presets/library.yaml`, `examples/halcyon-1/views/editorial.yaml`, `examples/halcyon-1/themes/editorial.yaml`, or `examples/halcyon-1/contexts/13-gallery-editorial.yaml` to implement this issue.

## Slices, verification, and publication boundaries

| Slice | Files/owners | Focused evidence and acceptance gate | Publication unit |
|---|---|---|---|
| I1 — resources and regression gates | New package View/Theme, their two corpus mirrors, `src/chrona/resources/presets/default.yaml`, and the bundled-default/identity tests | Validate resource syntax/contracts in the isolated project venv; compare package and corpus bytes; verify only View/Theme selection changed. Run `./.venv/bin/python -m pytest -q tests/integration/test_readable_defaults.py tests/integration/test_packaged_resources.py` (or the narrower identity-test node). Exercise the real bare CLI path and `chrona init` starter without presentation overrides; assert Scene and SVG row/label/suppression properties. Keep any pinned `default-draft` test visibly supplemental. Run `./.venv/bin/python tools/check_starter_perceptibility.py`; require PASS. | One atomic resource-and-test commit after focused checks pass, so the first published default change has its regression guard. |
| I2 — tune and record public visual evidence | `docs/research/presentation/issue-498-bundled-default-readability-evidence-2026-09-27/` and only if required, the new Theme YAML plus byte mirror | Render bare HALCYON-1 through `chrona render examples/halcyon-1/project.yaml --actual examples/halcyon-1/actual.yaml` to Scene/SVG; initialize a clean starter with public `chrona init`, render without overrides, and capture its Scene/SVG. Produce PNGs using the supported SVG/image tooling. Inspect the two default outputs at readable scale and compare side by side with generated slide 13. Confirm the alternate warm tint is perceptible, passes `starter-perceptibility`, and remains well below column ground; preserve Editorial palette, type system, and axis. Tune only the Theme token/opacity and its mirror if evidence requires it; rerun I1 gates after tuning. Record all expected and unexpected Scene/SVG byte changes. | One evidence commit, including any final YAML tuning and matching mirrors; do not commit trial renders. |
| I3 — public materializers and release gate | Existing corpus/public materializer files should remain unchanged unless verification proves a declared output needs regeneration; if so, update only the affected declared evidence and its source context under separate review | Run `./.venv/bin/python tools/regenerate_public_examples.py --check` (repository CI also runs `tests/integration/test_materialize_example.py::test_declared_examples_reproduce_by_public_cli`). Verify no unintended public materializer changes. Run the full three-OS CI release matrix: pytest/conformance, wheel/smoke, and newest-Python public-materializer evidence. Inspect the completed CI run and classify every failure. Acceptance review compares before/after generated artifact hashes/bytes and reports no unexplained changes. | CI result is evidence, not a local commit; if generated declared artifacts change, publish them in a separate coherent artifact commit before acceptance review. |
| I4 — acceptance review | New review document only | Fill the literal four-row acceptance table with direct evidence. Include resource SHA-256 mirror checks, bare render commands, init starter commands, perceptibility result, Scene/SVG inspection, side-by-side image review against slide 13, palette/type/axis comparison, public materializer check, three-OS CI links, and exact commits. State current published base and keep issue open if any evidence is missing. | Publish review separately after implementation and CI evidence. Do not close #498 in this plan. |

Create an isolated `.venv` in the implementation worktree and install the project's development/render extras and required font package there; use that environment for all local Python commands. Do not install packages globally or rely on another worktree's editable installation. Focused commands above are planned verification, not claims that they have been run. Full local pytest is not duplicated; the CI matrix supplies the three-OS suite and release checks as specified by repository workflow.

## Output inspection requirements

For HALCYON-1 and the initialized starter, record row count, selected bar count, alternate row-band geometry, visible member-label count, and suppression count/identities. Confirm each row has continuous visual guidance through the plot's end (alternating fills may guide adjacent unfilled rows through shared edges; do not require one rectangle per row). For each visible label, prove in Scene bounds that it belongs to its object's own row and is anchored at that bar's end or start. For every name not visible, prove a corresponding suppression diagnostic and no hidden label primitive. Confirm rendered SVG expresses the same user-visible result; Scene-only checks do not close these criteria.

The visual batch must show the new default next to `13-gallery-editorial` at comparable scale. Review the row tint against both the paper and column ground, label legibility, palette, type, and axis. Explicitly verify the catalogue `editorial` output and slide 13 are unchanged/reference-faithful. The generated evidence is checked into the issue evidence directory only after visual and automated gates pass; preserve source, Scene, SVG, and rendered comparison image together.

## Design-return triggers

Pause the affected slice and publish a design correction, architecture review, and implementation-plan amendment before proceeding if:

- current published Layout cannot honor row-local end → start → suppress placement or provide accountable suppression diagnostics through the selected bundled View;
- alternating row grounds cannot produce continuous row guidance to plot end, or require new View/Theme/schema or Layout geometry semantics;
- no opacity/tint both passes the official `starter-perceptibility` check and is visually just perceptible while remaining well below column ground; a hairline rule is a B-depth successor, not an ad hoc extension of this slice;
- the owner's “small navy type” requires a new semantic role or typography contract because the existing Editorial text treatment does not fit/read acceptably;
- resource identity/package resolution would alter the named Editorial catalogue entry, gallery slide 13, explicit preset selection, or immutable Context behavior;
- a product-code, schema, CLI, adapter, normative-specification, or #466/#467 dependency is discovered;
- a required public materializer output changes beyond the reviewed default/starter evidence or the three-OS CI gate exposes a contract conflict.

Do not use a local conditional or hidden resource override to bypass one of these triggers. Recheck issue #498 and published `main` before every publication; publish design, implementation plan, implementation, and acceptance review as separate serial units. Before any push, fetch `origin/main`, verify ahead/behind state and exact target commits, inspect staged/generated diffs, and stop to reconcile an unexpected update. This plan authorizes no commit, push, issue update, or issue closure.
