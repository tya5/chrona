# Architecture Review — Presentation Diagnostic Aggregation (#450)

**Decision:** accept.

The collection phase is correctly located before typed closure construction.
It avoids contaminating Layout/Scene with malformed resource values and avoids
the opposite failure of validating only the first resource.  Retaining
`parse_contract` as the sole typed constructor prevents a parallel permissive
parser.  Explicit prerequisite suppression makes diagnostic completeness
honest: unknown declarations are not fabricated, while independent known
resources are always checked.  The design preserves #449's rule that valid
fit constraints render; this issue applies only to invalid ingress.
