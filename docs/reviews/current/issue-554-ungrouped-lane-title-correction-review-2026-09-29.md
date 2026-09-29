# Issue #554 — Ungrouped lane title architecture review

**Decision:** approve the [correction](../../design/issue-554-ungrouped-lane-title-correction-2026-09-29.md) before changing product code. The failed attached-milestones render proves a valid no-group lane was outside the original title rule.

Project supplies the founder's authored title; the Review projection supplies deterministic member order; View still selects `lane` versus `group` presentation. No generated identity is used as display text. Lane membership, Layout geometry, Scene provenance, and SVG adapter behavior remain unchanged under Specs 08/38/50. The rule supports #554's no-raw-ID acceptance without requiring a new authoring field. Focused tests must cover ungrouped multi-member lanes and missing member titles; public attached-milestones CLI rendering must succeed.
