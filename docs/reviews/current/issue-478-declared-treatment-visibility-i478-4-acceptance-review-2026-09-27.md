<!-- chrona:literal-acceptance/v1 -->

# Release Review — Declared Treatment Visibility (#478)

**Reviewed public base:** `90306256219a1888fb674bf8677d28739eca244d` (`main`).
**Observed:** 2026-09-27. **Implementation slices:** I478-1 `0a846388`, I478-2
`bd7dfaca`, and I478-3 `cf09ab1d` (PR [#495](https://github.com/tya5/chrona/pull/495)).
**Authority:** [Issue #478](https://github.com/tya5/chrona/issues/478),
[implementation plan](../../planning/active/issue-478-declared-treatment-visibility-implementation-plan-2026-09-26.md),
[current I478-3 plan amendment](../../planning/active/issue-478-role-admission-implementation-amendment-2026-09-27.md),
[design](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md),
[whole-architecture review](issue-478-declared-treatment-visibility-architecture-review-2026-09-26.md),
and the [I478-1](issue-478-declared-treatment-visibility-i478-1-review-2026-09-26.md),
[I478-2](issue-478-declared-treatment-visibility-i478-2-review-2026-09-26.md),
and [I478-3](issue-478-role-property-admission-i478-3-implementation-review-2026-09-27.md)
slice reviews. This review supports final issue acceptance; it is separate from product implementation.

## Literal issue acceptance

### Issue #478

- Source: [Issue #478](https://github.com/tya5/chrona/issues/478)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it. | met | [Default/rich SVG integration test](../../../tests/integration/test_render.py#L135) verifies the two Scene facts and two CLI info records (`linear-gradient` and `drop-shadow`, both recommending `chrona-output/visual/v0.6-svg`); it checks that rich Scene paint contains both effects and SVG output contains `<linearGradient>` and `<filter>`. [I478-2 review](issue-478-declared-treatment-visibility-i478-2-review-2026-09-26.md) records the target-profile matrix and rich PNG pixel comparison. Current-main manual render reproduced both exact default Scene diagnostics for SVG and PNG; rich Scenes had no omission diagnostic. Rich SVG contained six gradient bands and six shadow filters. | — |
| 2 | A Theme property on a role that cannot carry it is diagnosed at load time. | met | [Direct-role and Scheme-target pointer tests](../../../tests/unit/chrona/presentation/test_role_admission.py#L60) assert `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at the exact declaration pointer. [Public consumer/Theme structural sweeps](../../../tests/unit/chrona/presentation/test_role_admission.py#L112) cover every authored Theme declaration and emitted Scene role/kind pair; [Theme closure sweep](../../../tests/unit/chrona/presentation/test_role_admission.py#L143) resolves all authored Theme roots. [I478-3 review](issue-478-role-property-admission-i478-3-implementation-review-2026-09-27.md) inventories the atomic migration and exact generated-output comparison. | — |
| 3 | Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed. | met | [Completed suppression integration test](../../../tests/integration/test_render.py#L67) checks the count equals the two placement warnings, suppressed labels have no drawable Text primitive, and CLI emits one `severity: info` record. The generated Scene carries `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=2`. See also [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md#L67) and [I478-1 review](issue-478-declared-treatment-visibility-i478-1-review-2026-09-26.md). | — |

## Programme-level criteria (optional)

No additional programme-level criterion is used to substitute for the three literal Issue #478 rows.

## Acceptance verification

- Focused current-main command in this worktree's isolated `.venv`: `.venv/bin/python -m pytest -q tests/unit/chrona/presentation tests/integration/test_render.py tests/integration/test_issue_478_role_admission.py tests/cli/test_cli.py` — **783 passed**, 4 upstream deprecation warnings, 138.35 seconds.
- Public materializer command in the same `.venv`: `.venv/bin/python tools/regenerate_public_examples.py --check --jobs 4` — **PASS, 28 slides**; generated files remained clean. `.venv/bin/python tools/check_issue_acceptance_reviews.py` also passed.
- Actual current-main render inspection used HALCYON-1 with the copied `elevated-light` bundle. The default SVG and PNG Scenes each reported the group-band gradient and shadow omissions with target-correct `v0.6-svg` / `v0.6-png` suggestions. Rich SVG and PNG Scenes reported neither omission. Rich SVG serialized six group-band gradients and six shadow filters. The baseline and rich PNG images were rendered and inspected; the pixel-difference assertion is retained in the [PNG adapter test](../../../tests/unit/chrona/presentation/renderers/test_target_registry.py#L310). These temporary inspection artifacts are not committed; the reproducible test assertions and slice reviews above are the durable evidence. The public corpus has no committed PNG materializer.
- The migration/output batch is detailed in [I478-3 review](issue-478-role-property-admission-i478-3-implementation-review-2026-09-27.md): 24 Theme sources updated; 55 direct role-property declarations and 133 Scheme targets removed after consumer audit; 28 Scenes regenerated. All 28 SVG outputs were byte-identical. Parsed Scenes were identical after excluding Theme provenance and unsupported Text-role `stroke`/`strokeWidth` payloads; the 119 removed payloads were `variance-behind` (88) and `annotation` (31). No supported visible treatment, Scene geometry, primitive identity, routing, or text placement changed.
- [Post-merge main CI run 36284398114](https://github.com/tya5/chrona/actions/runs/36284398114) passed all four jobs at I478-3 commit `cf09ab1d`: Ubuntu, macOS, Windows conformance/full pytest/wheel smoke, and newest-Python public-materializer reproduction. The reviewed public base is a later docs-only main commit; this review reran the issue-focused tests and all 28 materializer checks against that base. No duplicate full local suite was run.

## Architecture conclusion

The three acceptance paths stay within the approved owners: Layout counts completed suppressed member-label placements; Theme/Scheme closure validates direct and inserted role-property bindings against the Scene-owned finite consumer projection; Scene resolves profile-dependent paint and transports typed omissions; the CLI projects those completed facts; adapters serialize completed Scene paint only. Default-profile omission remains informational and never upgrades the profile. Rich profile rendering demonstrates the group-band treatments survive SVG and PNG materialization. The Theme migration removes only properties with no capable consumer and preserves valid `planned` shadow support.

The published I478-3 corrections and amendments resolved the role/consumer gaps discovered during implementation. Current tests, Theme sweeps, and output evidence expose no remaining unclassified consumer, Scene/CLI mismatch, adapter loss, or pixel contradiction requiring another design correction. All three literal criteria are met on the reviewed base. This review is the acceptance evidence needed for the separately authorized issue-close step; the issue remains open until its owner publishes this review and closes it.
