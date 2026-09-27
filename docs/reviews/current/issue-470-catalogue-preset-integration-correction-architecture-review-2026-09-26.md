# Architecture Review — #470 Combined-Merge Correction

**Design correction:** [combined preset contract](../../design/issue-470-catalogue-preset-integration-correction-2026-09-26.md). **Trigger:** owner clarification on #470 and PR #485.

| Adjacent authority | Consistency result |
| --- | --- |
| Specification 50 natural canvas | Requested 1600 × 900 may grow; actual dimensions stay visible in evidence. |
| Specifications 06/07/08/33 | View, Theme, Layout and Scene ownership is unchanged by the YAML-only merge. |
| Specifications 51/55 and #378 genericity | Distinct preset members, exact library identities and starter compatibility remain mandatory. |
| #400/#449 diagnostic honesty | TVAC and label-suppression facts remain emitted and inspected; they are not reclassified as fit success or silently dropped. |
| #466 obstacle work and #476–#483 gaps | Future mechanism changes keep their separate issue and design gates. |
| Publication safety | One combined reviewed PR resolves shared-test conflicts; exact union and current-main integration are verified before merge. |

**Decision:** approve the correction for implementation planning. A single
combined PR is coherent because the five independent bundle changes and
shared packaging assertions form one conflict-free reviewable unit. The risk
is treating an allowed state/suppression diagnostic as permission to overlook
an actual geometry failure; the acceptance review must list all emitted
diagnostics and match the defined failure class explicitly. No unresolved
architectural inconsistency or normative-specification change remains.
