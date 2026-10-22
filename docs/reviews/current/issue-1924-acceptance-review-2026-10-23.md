<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1924 rows 1 to 3

Observed on `main` at `e3ec09e9f` (the derived-sync bot commit after [PR #1933](https://github.com/tya5/chrona/pull/1933)). [Issue #1924](https://github.com/tya5/chrona/issues/1924) is the follow-up of the `narrowed` row 3 of [#1913](https://github.com/tya5/chrona/issues/1913) (see [issue-1913-acceptance-review-2026-10-22.md](issue-1913-acceptance-review-2026-10-22.md)). It has three bullets under `Acceptance:`; its two comments (dev B's status naming the rule and the decision that relations do not opt in, and dev A's report of the derived-gate race that was fixed by #1932) add no acceptance clause. They were re-fetched with `gh issue view 1924 -R tya5/chrona --json body,comments` on 2026-10-23 and counted literally: three rows. Landed: [PR #1927](https://github.com/tya5/chrona/pull/1927) (`4faae80ca`), with the bot commit `6ccaf8c6e`. All three rows are `met`.

## Method

Private venv `/private/tmp/claude-501/venv1682`, `PYTHONPATH=<worktree>/src:<worktree>:<worktree>/packages/chrona-fonts-noto-cjk/src`, worktree on `origin/main` `e3ec09e9f`; the before render used a second detached worktree at `4faae80ca^` (`734483472`). Inputs: `trial-17/plan/B-en-{project,actual,baseline}.yaml` from commit `cbc183f6b` (`git show`), rendered in both trees with `chrona render --preset yuya --locale en-US --actual B-en-actual.yaml --snapshot B-en-baseline.yaml --emit-scene`; the before SVG is byte-identical to the one recorded in [yuya-b-en-gap.txt](assets-1913/yuya-b-en-gap.txt) (`cmp`). The numbers come from one read-only probe, [probe-1924.py.txt](assets-1924/probe-1924.py.txt), run on the emitted Scenes; its log is [probe-1924.log](assets-1924/probe-1924.log), and the SVG after is [yuya-b-en-after.svg](assets-1924/yuya-b-en-after.svg). Tests: [pytest-1924.txt](assets-1924/pytest-1924.txt) (203 passed, `test_ports.py`) and [pytest-1913-main.txt](assets-1913/pytest-1913-main.txt) (251 passed, with `test_annotation_search.py` and `test_obstacles.py`).

## Literal issue acceptance

### Issue #1924

- Source: [Issue #1924](https://github.com/tya5/chrona/issues/1924)
- Observed: 2026-10-23

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On the trial-17 B-en yuya render the a1-note leader starts within 0.1 units of the painted glyph edge (measured in the SVG, before/after numbers stored). | met | Before: leader start x=843.685, painted edge x=841.840, gap 1.845. After: leader start x=841.840, gap 0.000, from the emitted Scene (`points[0]` of `annotation-leader:a1-note` is 841.83984375 against the stroke part's 841.33984375 plus half of the 1.0 stroke) and from the SVG path `d="M841.84 515.183L843.685 515.183L843.685 586.25L1308 586.25L1308 508.863"` ([log](assets-1924/probe-1924.log), [SVG](assets-1924/yuya-b-en-after.svg)). Between the two renders exactly one path line differs. The numbers are stored in this review's assets and in the PR body. | — |
| 2 | A synthetic compound glyph with a slit across the cardinal axis selects the painted port. | met | `test_axis_in_a_slit_between_fill_slices_takes_the_painted_port` builds two fill slices separated by a 0.6 slit across the axis and asserts the `end` port is (117.5, 60) and `start` (103.5, 60) with `painted=True`, the egress candidate's semantic port 117.5 (within 0.1), the exposed port still the viewport tip 120, and relations keeping 120; `test_wide_gap_between_painted_parts_is_not_bridged` asserts a 6.0 gap is not bridged ([`test_ports.py`](../../../tests/unit/chrona/presentation/layout/test_ports.py), [log](assets-1924/pytest-1924.txt)). The rule is in [`ports.py`](../../../src/chrona/presentation/layout/ports.py) (`painted_cardinal_ports`). | — |
| 3 | Diamond/ordinary ports, endpoint exemptions and nonhost clearance unchanged; side effects reported as a count table. | met | The unchanged-behaviour tests of #1913 still pass: `test_diamond_and_ordinary_point_ports_stay_on_viewport_tips`, `test_relation_ports_keep_the_viewport_tips_of_a_compound_glyph`, `test_compound_glyph_keeps_nonhost_clearance_and_registered_port_authority` and, in the other two files, `test_routed_tail_exempts_only_the_named_source_port_on_egress` and `test_egress_exempts_only_named_host_on_that_segment` ([log](assets-1924/pytest-1924.txt), [log](assets-1913/pytest-1913-main.txt)). The count table is in the PR #1927 body: 1 of 50 public slides changed (`halcyon-1` 22-yuya, `annotation-leader:window-note`, 1 path, 0 routes, labels or primitives added or removed), 0 new diagnostics, no schema delta. The published slide agrees: its leader starts at x=1168.715, on its host glyph's painted edge (gap 0.000, [log](assets-1924/probe-1924.log)), and the bot commit `6ccaf8c6e` changes only that slide's SVG and Scene and the diagnostics inventory. | — |

Counts: 3 rows, 3 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Public side effects

This review adds a document, logs, one probe script copy and one SVG under [assets-1924](assets-1924/probe-1924.log); it changes no code, schema, specification, guide, preset, design, example or workflow.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |

The public effect of the reviewed PR is in its own body: 1 of 50 slides, 0 new diagnostics, no schema delta. Relation routing on compound glyphs still uses viewport tips; that is the decision recorded on #1924, not one of its three rows.
