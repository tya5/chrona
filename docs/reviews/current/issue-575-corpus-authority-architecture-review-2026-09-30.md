# Architecture Review — Corpus Used as Authority for the Core (#575)

**Decision:** Accepted with corrections. The design direction is sound; the
gaps below are fixed in the implementation plan and, for the link, in the design.

Reviewed: the [design](../../design/issue-575-corpus-authority-design-2026-09-30.md),
the issue and its owner comment, `AGENTS.md`, Spec 50 §3-§5, and the current
tests and data on `main` `22ea2c1c`.

## What holds

- Judging core rules by synthetic fixtures and using the corpus only as evidence
  is the layering AGENTS.md already prescribes. The design adds tests, not
  product behaviour, so no Layout, Scene or adapter ownership moves.
- Freezing three Layout Profiles for the engine tests is the right isolation: an
  example edit can no longer move an engine assertion.
- Deferring `attached-milestones` until #573 avoids restoring data that the
  current core cannot yet lay out.

## Findings

1. **Broken link (fixed).** The design links to
   `issue-575-corpus-authority-design-plan-2026-09-30.md`, which does not exist.
   AGENTS.md asks for one work record; the design now links the implementation
   plan, which carries the baseline.
2. **Restoring `2wd` re-breaks the #467 chain row, and the design does not say
   so.** The 4wd edit existed because avionics' actual finish (2027-04-30)
   overlaps a 2wd bus-test start (2027-04-29), so the lane rule cannot keep
   `structure -> avionics -> bus-test` on one lane. After the restore that chain
   splits on HALCYON `02`. Acceptance row 1 allows the restore only if the look
   is reached "through YAML or a general knob", and no such knob is proposed.
   This review does not invent one: #467 is closed, the rule (a chain continues
   when date intervals do not overlap) is already covered by synthetic tests
   (`test_lane_membership.py`, `test_projection_rows.py` with fixed dates), and
   the design accepts an output change judged against the rule and targets. The
   consequence must be reported in I575-3, not discovered by a red test. If the
   owner wants the chain on one lane at 2wd, that is a new general rule (for
   example, tolerating touching or actual-overlapping intervals on a chain)
   needing its own design, not a data edit.
3. **Corpus-position tests the design omits.** Three tests hard-code the 4wd
   data: `test_halcyon_four_workday_lag_places_bus_test_on_may_third` and
   `test_every_halcyon_context_pins_current_project_without_repinning_theme`
   (a literal sha256) in `test_materialize_example.py`, and
   `test_halcyon_02_data_only_lane_oracle_has_named_chain` in
   `test_projection_rows.py`, which asserts the chain of finding 2 from corpus
   data. The lag arithmetic already has scheduler tests and the chain rule has
   synthetic tests, so these are rewritten as evidence of the restored data, not
   deleted silently. I575-3 lists them.
4. **"Fails if broken" is not in the design.** Synthetic tests that pass
   trivially would satisfy the letter of row 2. Every I575-2 test therefore gets
   a mutation check (break the behaviour, watch the test fail), recorded in the
   PR body.
5. **Guard depth.** Validating frozen profiles only against the schema would miss
   semantic drift. The guard also resolves each through
   `resolve_layout_profile`. Because schema changes such as #573's are additive
   under Spec 56 §3.2, the fixtures stay valid; a breaking version change fails
   the guard, which is the intended signal to migrate them deliberately.
6. **Test (c) vs #573.** #573 changes the member-name end-gap bound and search
   policy. The row-band test asserts only that every visible label lies inside
   its row band (otherwise counted as suppressed), which #573 does not alter; it
   does not pin the 2 em bound or the search side.
7. **Acceptance rows 3 to 5 need evidence, not work.** They are already met; the
   acceptance review must cite Spec 50 §5 and AGENTS.md rather than re-edit text.
8. **Re-pin token.** Contexts pin `example-v2` for the 4wd bytes. Changing bytes
   under the same token would violate revision immutability, so the restore uses
   a new token with the new `contentIdentity`.

## Residual risks

- The restored HALCYON slides may look worse than today's (chain split, extra
  lane). That is admissible under the issue: today's output is not an oracle. The
  I575-3 review states whether each changed primitive follows from the rule.
- Byte identity is reported only where a slice intends no behaviour change
  (I575-1, I575-2). It is not offered as a quality claim for I575-3.
