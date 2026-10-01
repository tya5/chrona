<!-- chrona:literal-acceptance/v1 -->

# Issue #792 — `deadline` is read and `W_DEADLINE` is emitted: acceptance review

Source: [Issue #792](https://github.com/tya5/chrona/issues/792), observed 2026-10-02 (body plus one owner comment, last updated 2026-10-01T16:56:52Z). The issue has one acceptance checkbox; the table splits its two alternatives and the conformance clause. Work record (baseline, decisions D1 to D10, design, plan): [issue-792 work record](../../planning/active/issue-792-deadline-warning-work-record-2026-10-02.md); living contract [Spec 04](../../specification/04-scheduling-model.md) section 10 and [Spec 66](../../specification/66-agent-interface.md).

Slices: work record [PR #818](https://github.com/tya5/chrona/pull/818) (`e253699a`); implementation [PR #826](https://github.com/tya5/chrona/pull/826) (`09fa4628`, `I792-S1`). Successor: [#822](https://github.com/tya5/chrona/issues/822) (a View mark for a slipped deadline and a terse `deadline` clause).

## Literal issue acceptance

### Issue #792

- Source: [Issue #792](https://github.com/tya5/chrona/issues/792)
- Observed: 2026-10-02

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `W_DEADLINE` is emitted for an object placed after its `deadline` (a test with a fixed-span task and a derived gate) | met | [`core/deadlines.py`](../../../src/chrona/core/deadlines.py) `deadline_warnings`; [`test_deadlines.py`](../../../tests/unit/chrona/core/test_deadlines.py) `test_a_fixed_span_and_a_derived_gate_past_their_deadlines_each_warn_with_details` (exact message and `details` for a fixed span and a `scheduled-point`), with the equal-date, `at`/`end`, rollup, ordering and inertness cases beside it. Surfaces: `chrona schedule` `warnings` (goldens `schedule-deadline-warning`), MCP `schedule_project` `warnings` ([`test_agent_tools.py`](../../../tests/unit/chrona/app/test_agent_tools.py)), `render` stderr and Scene diagnostics with the SVG byte-identical ([`test_deadline_render.py`](../../../tests/integration/test_deadline_render.py)). Ten mutants of the new code and callers were all killed (PR #826 body). | — |
| 2 | ... or the spec states it is not, and the conformance subset is consistent with whichever | met | The first branch was built, so the spec says it is emitted: [Spec 04](../../specification/04-scheduling-model.md) section 10 defines the rule and `details`, section 23 still lists "deadline diagnostics" and is now true of the reference scheduler, [`core-v0.1-diagnostics.md`](../../specification/supplemental/core-v0.1-diagnostics.md) row `W_DEADLINE`, [Spec 66](../../specification/66-agent-interface.md) the `warnings` field. The stale statements in the skill and `mermaid-or-chrona.md` ("no diagnostic") were corrected and the skill tests pass. | — |
| 3 | (Issue body, "Decide") the soft promise: the `render` warning first, then the `schedule` JSON field agreed with #142, then the View mark as its own issue | narrowed | The `render` warning and the `schedule` and MCP field shipped (decisions D4 to D6, recorded on the issue; the #142 agent interface had shipped, so its record shape was reused). The View mark and the terse clause are not built: [#822](https://github.com/tya5/chrona/issues/822). `chrona validate` deliberately does not judge a deadline (D7: it computes no placements). | [#822](https://github.com/tya5/chrona/issues/822) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

`deadline` stays a promise and never a bound (Q-SCHED-2, Spec 04 section 19): the scheduler never reads it, and a test shows that a violated deadline changes no placement, verdict or analysis. The evaluation is a pure Core function over placements (precedent `attachment_warnings`); use cases assemble it, adapters serialize it, and import direction and module reachability are unchanged. The pair "derived gate plus deadline" is complete in meaning: `scheduled-point` computes, `constraints.at.max` rejects, `deadline` warns. Public change: `chrona schedule` stdout gains an always-present `warnings` array (three goldens changed by exactly that line), a non-date `deadline` is now `E_SCHEMA`, and MCP `schedule_project` gains `warnings`.

Disclosures:

- No committed Project warns (the `corpus` sweep passes), so no public artifact changed; the SVG of a plan with a missed deadline is byte-identical to the plan without it, because no View mark exists (#822).
- A rollup's finish is its `end`; a scenario is judged only when it is the scheduled Project. Both are stated in Spec 04 section 10.
- Two sibling identifiers, `W_NEGATIVE_LAG` and `W_SUMMARY_DEPENDENCY`, listed in the diagnostics table are still not emitted; they are outside this issue.
- The `diagnostic-inventory` conformance check is stale in a local worktree until the main sync regenerates it; CI's snapshot is green.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #792; record that run in the issue closing comment.
