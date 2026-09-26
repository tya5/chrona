# Architecture review — as-of mark clearance (#458)

**Correction:** [mark-clearance design](../../design/issue-458-as-of-mark-clearance-correction-2026-09-26.md).

Accepted. Specification 50 owns ranked candidates and Layout placement;
the new fallback-side field is typed Layout policy with a default preserving
ordinary labels. It does not move geometry into Scene. Specification 08 and
#446 remain independent observers, while the generated-output acceptance
test supplies the additional text/mark property. The seam can contain axis
labels, so normal candidate search must include them as obstacles before a
declared visible fallback is used. Remaining risk is broad output churn;
the implementation must inspect every changed public artifact.
