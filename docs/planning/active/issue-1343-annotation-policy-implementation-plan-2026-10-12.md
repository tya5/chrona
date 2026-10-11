# Annotation-policy implementation plan (#1343)

[Published design](../../design/issue-1343-annotation-policy-design-2026-10-12.md)
and [architecture review](../../reviews/current/issue-1343-annotation-policy-architecture-review-2026-10-12.md).
Start product changes only after the already-active PR1423 publication lane clears.

| Slice | Owners/files | Acceptance and verification |
| --- | --- | --- |
| 1. Closed declarations | `schemas/view-v0.28.schema.yaml`, `schemas/layout-profile-v0.10.schema.yaml`, shared schema parts; `contracts/resources.py`, `contracts/view_defaults.py` | Optional additive properties; shared candidate vocabulary; whole-member replacement; invalid declaration/policy tests; strict schema equivalence. |
| 2. Semantic expansion | Pure Presentation helper called by `review/v05_content.py` | Different Project notes, point/span/any, filtering/folded membership, ghost deduplication, binding/key order, explicit overrides, identity/policy rejection and truthful source refs; immutable inputs. |
| 3. Output acceptance | Synthetic/test-local fixtures and focused integration tests | All five designs drop their per-id list locally and place HALCYON's three notes identically; another Project places its notes by kind. Compare actual Scene/SVG primitives, geometry, paint and diagnostics; preserve all legacy declaration bytes. |

Reuse ordinary typed annotation intents and existing Layout candidate completion;
do not add Scene/adapter placement or Project-specific rules. If completion
reveals a missing contract, return to design before altering product behavior.
Permanent `examples/**` migration is reviewer-owned; no authored managed evidence.
Extend existing dependency-network annotation exclusions to both new members;
test rejection rather than accepting intent its Layout cannot complete.
Publish coherent implementation/test/review units in one eventual PR; inspect
its CI-owned public snapshot as a batch, focused tests and schema gate locally,
full three-OS containing-review release in CI. Keep both literal criteria open
until direct rendered evidence and release gates prove them.
