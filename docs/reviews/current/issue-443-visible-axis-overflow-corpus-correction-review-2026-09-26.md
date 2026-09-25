# Architecture Review — Visible Axis Overflow Corpus Correction (#443)

**Design under review:**
`issue-443-visible-axis-overflow-corpus-correction-2026-09-26.md`.
**Decision:** Accepted for implementation planning.

## Boundary review

| Boundary | Result | Evidence / guardrail |
| --- | --- | --- |
| View → Layout | Pass | The changed overflow declaration remains a finite View policy; Layout retains authority for measuring and applying deterministic thinning. |
| Layout → Scene | Pass | Retained labels, omitted-candidate outcomes, density diagnostics, warnings, and geometry are completed Layout facts. |
| Scene → adapter | Pass | Adapters serialize the selected completed primitives; none decides which month label to omit or changes axis coordinates. |
| #449 failure policy | Pass | `visible-overflow` remains available for inputs that explicitly choose every label; the corpus selects its published `thin-with-record` alternative. |
| #446 observation | Pass | The correction creates no finding exemption or numeric allowlist.  The evaluator will observe retained text and recorded thinning normally. |

## Findings

1. The #443 literal acceptance is a corpus release requirement, not a claim
   that #449 forbids all explicitly elected visible-overflow geometry.  The
   acceptance review must state that distinction.
2. Replacing the View declaration is sufficient only if the regenerated Scene
   records each thinned candidate and an axis-density diagnostic.  A source
   edit without those facts is not accepted.
3. The completed-corpus audit compares geometry at the existing micro-point
   tolerance.  It must not classify decimal conversion residue as an
   intersection, and it must continue to reject the measured Jun/Jul overlap.

## Conclusion

The correction preserves the architecture's one-way ownership and resolves
the discovered contradiction at the policy-selection boundary.  It authorizes
a narrow implementation-plan amendment and the corresponding View/evidence
publication; it does not authorize a generic Scene overlap exception or a
change to #449's fallback registry.
