# Design Correction Plan — Fiscal Calendar Contract (#405, #406, #407, #408, #400)

**Trigger:** The live `timeline/project/v0.6` calendar contains working days
and exceptions but no fiscal-start fact. View v0.17 alone cannot implement the
accepted calendar-owned fiscal behavior.

1. Publish a project-v0.7 fiscal-calendar correction and architecture review.
2. Amend I1 to migrate View v0.17 and Project v0.7 atomically, including every
   Context closure and public corpus resource.
3. Implement calendar bucketing only after both source contracts exist.
