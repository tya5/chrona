# Design Correction — Do Not Inflate a Fixed Host's Canvas (#468)

**Corrects:** [coherent allocation design](issue-468-coherent-draft-allocation-design-2026-09-26.md).

## Discovery

The first implementation probe used the Draft-auto extent formula for every
table-timeline profile. Batch regeneration exposed two valid fixed-host
profiles whose timeline capacities do not grow with the viewport:

- HALCYON `03-launch-campaign`: timeline remains 800 high and notes remain
  at y=976.2, but the computed canvas increases from 1120 to 1376.
- HALCYON `11-overlay-briefing`: timeline remains 914 high; its anchored
  placement shifts down 110.75, and the canvas increases from 1560 to 2446.

Neither change allocates more row space. Publishing it would create a large,
unrelated artifact delta and falsely imply coherent reflow.

## Corrected rule

For each declared content host, Layout compares its allocation at the
requested extent and at a finite probe. It computes a candidate larger
extent only if the candidate's final arrangement actually satisfies every
declared requirement. If a valid fixed/max/anchored profile cannot satisfy
them, Layout returns the original requested extent unchanged; the existing
#449 natural placement, completed canvas and structured warnings report the
remaining shortage. No extra blank canvas or relocation is manufactured.
Invalid profile structure remains an error. This is source- and profile-
generic; it does not list the two HALCYON profile IDs in code.

This correction preserves the required result for growable normal-flow
profiles, including the default Draft. It intentionally does not claim that
an author-fixed 800-high timeline becomes 1000 high. A future explicit
authoring policy may choose to relax that profile constraint; #468 does not
silently override it.
