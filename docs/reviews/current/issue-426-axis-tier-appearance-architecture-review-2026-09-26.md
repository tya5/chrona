# Architecture Review — Axis Tier Appearance (#426)

**Predecessor:** [Design](../../design/issue-426-axis-tier-appearance-design-2026-09-26.md), [Specification 39 amendment](../../specification/39-axis-and-observation-clarity.md#12-axis-tier-appearance-426). **Reviewer note:** design-phase self-review, published for the lead's approval before implementation planning is treated as final.

## Layer boundary check

- **View** gains exactly one field, `typographyRole`, naming a Theme role — intent, never a pixel value. It does not gain a fill field: a band's fill is chosen by Layout's semantic-id-per-ordinal scheme and bound by Theme, keeping "which tier is emphatic" (View) separate from "what colour that means" (Theme). Consistent with the declared boundary.
- **Theme** gains no schema change; `roles` and `colorBindings` already accept arbitrary keys (confirmed at `schemas/theme-v0.11.schema.yaml:98-101,144`). The new roles (`axisQuarter`, `axisBandDecoration2`, `axisLabel2`, …) are ordinary role bindings, authored the same way `axis` is today.
- **Layout** owns the new lane cursor, the semantic-id ordinals, and the `axis_band_host`/`surface_quality.py` generalization. No geometry or fill decision moves to Scene or an adapter.
- **Scene/adapters** are unaffected: they already carry whatever semantic id and role Layout assigns; nothing about serialization changes.

No boundary is crossed. The design adds vocabulary (two new closed id ordinals per role, one View field), not a new owner.

## Consistency with adjacent designs

- **#482 (thinning schedule).** Untouched: `thinning_schedule` operates per-label-candidate within one tier's own fit measurement, independent of which Theme role that tier's typography resolves to. Moving the `text_treatment`/`metric_for` lookup inside the tier loop (§2.2 of the design) changes *which* metrics feed the existing fit test per tier, not the test itself.
- **#483 (band opacity 1 in every shipped Theme).** Untouched as a rule; it now applies per band role (`axisBandDecoration`, `axisBandDecoration2`, …) rather than to a single id. The derived Theme for the committed example must independently satisfy it for both new/reused band roles — a phase-2 authoring obligation, not a design gap.
- **#405/#406 (closed).** Confirmed out of scope; this issue is "how tiers look," not "which intervals appear or where." No overlap in code paths (axis interval selection in `layout/axis.py` is unmodified by this design).
- **#466/#467 (owned by another session).** No file this design touches (`layout/axis.py`, the axis section of `layout/surface_composer.py`, `layout/surface_quality.py`, `semantic_registry.py`, the View axis schema) overlaps annotation placement or lane rows. Confirmed no encroachment.
- **Specification 60 (declared colour scales).** Read in full for the #405 fold-in. Its eligible-target list (`planned` member marks only, field-tagged domain) does not today cover axis bands keyed by interval ordinal; extending it is named as a successor, not attempted. This is the correct boundary: Specification 60 owns *data-dependent* colour, and an axis interval ordinal is not a Project field, so folding it in without a new eligible-target case would blur "field source" into "structural position," which the specification's §1 boundary table explicitly separates by owner.

## The single-band carve-out (design §2.2)

This is the one piece of the design that is not a uniform rule, and it deserves explicit sign-off:

- **What it costs:** an implementer must branch on `len(band_tiers) == 1` before applying the new per-lane formula. It is a real, permanent conditional in `compose_surface_layout`, not a temporary shim.
- **What it buys:** all 21 public materializers, all 18 committed Views, stay byte-identical without any Theme edits. Only the one new committed example (design §4) changes rendered output, and that change is fully attributed by construction (it is the only View exercising the new code path).
- **Alternative considered and rejected:** a uniform "band lane height is always derived from `typographyRole`, default `axis`" rule, with no special case. This is architecturally cleaner but changes every existing band's height from "whole axis slot" to "one line," since no existing View sets `typographyRole`. That would force re-attributing all 21 public materializer diffs in this issue's phase 2, when #426's own literal criteria do not require touching a single existing View. Rejected on proportionality grounds, consistent with the brief's instruction to keep existing slides byte-identical where possible.
- **Decision:** keep the carve-out, documented normatively in Specification 39 §1.2 ("a View declaring exactly one `band` tier is unaffected"), so it is a stated contract, not an implicit accident of implementation order.

## Semantic-id ordinal scheme vs. an open/dynamic scheme

Considered and rejected: synthesizing ids at runtime (e.g. `f"axisBandDecoration:{n}"` for arbitrary `n`), which would let a Theme bind roles the registry never declared. Rejected because `semantic_registry.py`'s own docstring states the vocabulary is closed and curated ("every visual meaning ... is declared here once"); an open synthesis would let a View silently require a Theme role no reviewer ever sees listed. Two ordinals beyond the first are pre-registered because that is what literal criteria 1-4 require; a third is a small, visible, reviewable addition later, not a structural change.

## Correctness risk: host/contrast selection under multiple lanes

`axis_band_host`'s inline-only matching and `surface_quality.py`'s literal `"axisBandDecoration"`/`"axisLabel"` string checks were the two call sites most likely to be missed by a narrower fix (one that only touched the band-rendering branch). Both are named explicitly in the design (§2.4) with their exact current behavior and required generalization, because a text/host mismatch here would silently misreport or over/under-enforce contrast between a label and the wrong band — a correctness defect worse than the original issue, since it would look like a passing check.

## Decision

**Accepted for implementation planning**, contingent on the lead's sign-off on the single-band carve-out (the one deliberately non-uniform rule) and the choice of a new slide vs. a derived Theme for the committed example (design §3, left open on purpose).

## Unresolved items for the lead

1. Confirm the View version number (next after v0.23) to use when the schema field is actually authored in phase 2.
2. Confirm the single-band carve-out is acceptable, or direct a uniform rule and accept the full 21-materializer attribution cost.
3. Confirm two semantic-id ordinals beyond the default are sufficient for this issue's committed example (a third is a one-line follow-up if not).
