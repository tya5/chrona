<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1913 rows 1 to 3

Observed on `main` at `b1935990b` (the derived-sync bot commit after [PR #1923](https://github.com/tya5/chrona/pull/1923), `f846f5524`). [Issue #1913](https://github.com/tya5/chrona/issues/1913) was filed from dev A's #1906 SVG audit (dev A did not work it; dev B took it by the reviewer's lane change) and has three bullets under `Acceptance:`. The body and its two comments (the reviewer's lane change to dev B, and dev B's status naming the rule and the side effects) were re-fetched with `gh issue view 1913 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: three rows. The body also states a reproduction (Yuya B-en `a1-note` to `g1`, leader at the viewport edge 843.685, glyph outline about 841.340, 841.840 with the stroke, a gap of about 1.845). Landed: [PR #1923](https://github.com/tya5/chrona/pull/1923) (`f846f5524`): `connector_egress_candidates(painted=True)` puts the semantic port where the cardinal axis leaves the completed painted outline of a compound point glyph; only annotation leader placement and tail search opt in. Rows 1 and 2 are `met`. Row 3 is `narrowed`: the Yuya reproduction is not fixed, and relation routing still uses viewport tips; both are tracked on [issue #1924](https://github.com/tya5/chrona/issues/1924).

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>`, worktree on `origin/main` `b1935990b`, no shared install; the "before" render used a second worktree at `f846f5524^` (the parent of PR #1923). Focused tests: [pytest-1913.txt](assets-1913/pytest-1913.txt) (249 passed in `test_ports.py`, `test_annotation_search.py` and `test_obstacles.py`; the full suite was not run, and the local `E_MATERIALIZER_MISMATCH` of `test_materialize_example` is expected because the derived pipeline regenerates `examples/**`). The Yuya reproduction inputs are the issue's `trial-17/plan/B-en-{project,actual,baseline}.yaml` at `cbc183f6b`, rendered with `--preset yuya --locale en-US` in both worktrees; the numbers are in [yuya-b-en-gap.txt](assets-1913/yuya-b-en-gap.txt) and the SVG is [yuya-b-en-main.svg](assets-1913/yuya-b-en-main.svg). The two renders are byte-identical (same sha256 in the log). In this render the leader starts at y=515.183 (the issue quotes y=595.183 from the earlier WIP source); the x coordinate 843.685 and the glyph extents match the issue.

## Literal issue acceptance

### Issue #1913

- Source: [Issue #1913](https://github.com/tya5/chrona/issues/1913)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A synthetic inset compound point glyph selects a connector port touching its actual painted boundary toward the annotation box. | met | `test_inset_compound_glyph_ports_touch_the_painted_outline_not_the_viewport` builds a two-part glyph (filled diamond plus ring) inset in a 20x20 viewport with a completed outline stroke; with `painted=True` the `end` port is (116.5, 60) (fill edge 116 plus half the 1.0 stroke), the viewport tip is 120, the leader starts on the paint and crosses the inset inside its own host to the unchanged exposed port; `test_compound_glyph_without_stroke_part_ends_exactly_on_the_fill_edge` gives 116.0 without a stroke part ([`test_ports.py`](../../../tests/unit/chrona/presentation/layout/test_ports.py), [log](assets-1913/pytest-1913.txt)). The rule is in [`ports.py`](../../../src/chrona/presentation/layout/ports.py) (`painted_cardinal_ports`) and is opted into by [`surface_annotations.py`](../../../src/chrona/presentation/layout/surface_annotations.py) and [`annotation_search.py`](../../../src/chrona/presentation/layout/annotation_search.py), the annotation leader paths. Limit: the cardinal axis must cross a painted segment; a glyph with a slit on the axis falls back to the viewport tip (row 3). | — |
| 2 | Ordinary/diamond point ports and declared endpoint exemptions remain correct; connectors retain nonhost-mark clearance. | met | `test_diamond_and_ordinary_point_ports_stay_on_viewport_tips` pins the four ports and the first egress of an ordinary and a built-in diamond point with and without `painted`; `test_relation_ports_keep_the_viewport_tips_of_a_compound_glyph` pins the default (relation) path; `test_compound_glyph_keeps_nonhost_clearance_and_registered_port_authority` shows an unrelated mark still blocks beyond the exposed port and the painted port is the registered port of its own host. The declared exemptions are covered by the unchanged `test_routed_tail_exempts_only_the_named_source_port_on_egress` and `test_egress_exempts_only_named_host_on_that_segment`, which pass ([`test_ports.py`](../../../tests/unit/chrona/presentation/layout/test_ports.py), [`test_annotation_search.py`](../../../tests/unit/chrona/presentation/layout/test_annotation_search.py), [`test_obstacles.py`](../../../tests/unit/chrona/presentation/layout/test_obstacles.py), [log](assets-1913/pytest-1913.txt)). | — |
| 3 | Inspect actual SVG contact for the compound control and the Yuya reproduction; provide focused tests and normal release evidence. | narrowed | Focused tests exist and pass (row 1 and 2 files, [log](assets-1913/pytest-1913.txt)); the release evidence is the PR #1923 count table (3 of 50 slides, `halcyon-1` 21, 23 and 24, leader start moved by at most 0.5 unit, 0 new diagnostics, no schema delta) and its CI. SVG contact of the synthetic compound control was inspected only as unit coordinates (116.5 against 116 and 120), not as a rendered SVG. The Yuya reproduction is not fixed: the SVG before and after PR #1923 is byte-identical, `annotation-leader:a1-note` still starts at x=843.685 while the glyph edge is 841.340 (841.840 with the 1.0 stroke), a gap of 1.845 ([log](assets-1913/yuya-b-en-gap.txt), [SVG](assets-1913/yuya-b-en-main.svg)). Cause: the glyph is drawn as horizontal slices and the axis y=515.183 lies in a 0.584 slit between two fill slices, so `painted_cardinal_ports` found `above` and `below` but no `end`/`start` and used the viewport tip. The PR agent disclosed that the reproduction was approximated by a synthetic test, and relation routing still uses viewport tips. | [Issue #1924](https://github.com/tya5/chrona/issues/1924) |

Counts: 3 rows, 2 `met`, 1 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review updates a document and adds logs and one SVG under [assets-1913](assets-1913/pytest-1913.txt); it changes no code, schema, specification, guide, preset, design or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PR is in its own body: 3 of 50 slides, 0 new diagnostics, no schema delta.
