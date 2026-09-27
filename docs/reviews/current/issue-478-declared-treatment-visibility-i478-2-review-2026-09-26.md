# I478-2 Review — Optional Visual Treatment Dispositions

**Implementation:** `bd7dfaca03e6729e80544fda444ba0fa64b75aff` on `main`. **Public base:** `f5ac1f76` (I478-1 accepted). **Authority:** [#478 design](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md) and [implementation plan](../../planning/active/issue-478-declared-treatment-visibility-implementation-plan-2026-09-26.md). This is a slice review, not final issue acceptance.

## Verification and public bytes

- Focused local tests: `.venv311/bin/python -m pytest -q tests/unit/chrona/presentation tests/integration/test_render.py tests/cli/test_cli.py` — **606 passed**. They cover default/rich SVG and PNG, planned-mark rich shadow, exact Theme pointer, target-specific v0.6 suggestion, no available PDF suggestion, required-treatment rejection, deterministic deduplication, CLI info, Scene diagnostics, and PNG pixel difference.
- All 21 public materializers were regenerated in one bounded batch and `--check --jobs 4` passed. No committed Scene or SVG changed: the existing public contexts do not contain a decorative-optional treatment omitted by their selected profile. That zero-byte public diff is expected, not proof of the new behavior by itself; the copied `elevated-light` HALCYON render is the direct test fixture.
- Under the default SVG profile, six `elevated-light` group bands yield exactly two info facts: `group-band` `linear-gradient` and `drop-shadow`, each suggesting `chrona-output/visual/v0.6-svg`. The CLI prints their role, treatment, Theme pointer, selected profile, and paintable profile. Rich SVG has both completed effects on all six bands and serializes the gradient/filter, with no omission fact. The modified-Theme planned-mark fixture shows baseline omission and an actual rich SVG shadow on the mark. Rich PNG output is visually different from baseline pixels and has no omission fact; baseline PNG suggestions name `v0.6-png`.
- [CI run 36239753439](https://github.com/tya5/chrona/actions/runs/36239753439) passed all four jobs: Ubuntu, macOS, Windows conformance/full pytest/wheel and newest-Python public materializer reproduction. The local workspace's unrelated untracked `schemas/view-v0.23.schema.yaml` was untouched; clean CI is the authoritative full-conformance evidence.

## Architecture review

`resolve_scene_paint` now returns completed paint plus typed omission facts. The selected `VisualProfile` carries the target kind, so the suggestion does not infer it from the baseline ID. Scene deduplicates by role/treatment/profile/target and appends facts after Layout information; CLI projects typed facts and adapters continue to serialize completed paint only. Required treatments still reject before rendering. A planned-mark shadow is valid under the rich profile, consistent with the #391 capability ceiling and Specification 63. No geometry, primitive identity, SVG adapter policy, or source content changed.

## Literal Issue #478 criterion disposition after this slice

| # | Literal acceptance criterion | State | Evidence / next unit |
| ---: | --- | --- | --- |
| 1 | Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it. | met | HALCYON copied-preset Scene/CLI integration test, target-profile tests, rich SVG and PNG output checks above. |
| 2 | A Theme property on a role that cannot carry it is diagnosed at load time. | not met | I478-3 will add role/property admission and migrate dead declarations in one publication unit. |
| 3 | Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed. | met | [I478-1 review](issue-478-declared-treatment-visibility-i478-1-review-2026-09-26.md). |

I478-2 is accepted. The next public base is `bd7dfaca`; I478-3 may start. #478 stays open until role/property admission and final acceptance are published.
