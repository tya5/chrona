# Issue 1679: realized legend work record (2026-10-18)

Status: planning only. No behavior or implementation has been selected.

## Baseline and order

- Published `main`: `e69d4541a`. Preparation base: published S2 `2cdcc31e5` (PR 1687), not yet merged at plan drafting. The issue was found against `d11fd42b0`; reviewer-trial inputs are at `9fa6062de` on `reviewer/trial-5-inputs`.
- Start implementation only after #1680 and S2/PR 1687 are integrated. The issue comment explicitly calls for first inspecting semantic/scale-key identity and empty-column ownership, then publishing design and implementation plans.
- Current public Spec60 §4 separates semantic legend ownership from scale legends. The requested realized-paint completeness/suppression behavior therefore needs normative design and review before code.

## Literal acceptance criteria

1. A synthetic project with actuals, rendered with executive-light: every distinct realized mark paint has exactly one legend key, and the actual and progress keys use the realized paints.
2. When an encoding replaces the planned paint on every planned mark, no base planned swatch remains; the encoding's entries stand in its place. A mixed case (some planned marks unencoded) keeps the base key.
3. target-b without snapshot or actual has no baseline, actual or in-progress keys and no empty Δ column.
4. A count table of the public example changes, and the PNGs checked.

## Published facts and unresolved design questions

- S2 supplies completed paint/occurrence filtering in Layout; current filtering covers Style occurrences, not all final painted marks or progress shapes. Actual-range paint and progress are produced through distinct paths. Confirm the final paint witness and how it covers actual and progress without moving policy into Scene.
- Spec28 owns Detail semantic legend roles/labels and lists planned, actual, variance, milestone, and dependency. It does not settle progress-key naming, paint identity, deduplication, or how keys correspond to heterogeneous realized paints. Resolve these with Specs06/07/08/28/33/49/60 and #1682's field-profile/encoding work; do not duplicate that work's source defaults or resolver.
- Spec61 §1 currently requires a progress inset on its host legend key and forbids an inferred separate entry; Spec06 wording closure forbids synthesizing entries. Reconcile these explicit adjacent contracts with criterion1 before implementing derived progress keys.
- Determine whether semantic identity is a role, realized paint, source occurrence, or a composed key; how labels and ordering attach; and what “exactly one” means for equal paints from distinct semantic sources. No choice is made here.
- Define the observation domain for actual/progress keys and for planned encoding replacement: final painted occurrences, including cases with several actual colors, progress absent at zero, all planned marks encoded, and mixed encoded/unencoded marks. Decide identity/equality granularity only in design.
- “No snapshot or actual” and “no empty Δ column” need a precise source-availability/normalization rule. Existing table construction preserves declared columns and renders missing cells blank; existing omission paths concern unbound fields, not a general all-empty-column rule. Decide whether absence of the comparison source differs from a present source with blank values; no normalization behavior is selected here.

## Responsibility boundaries and design slices

1. **Evidence and ownership audit:** trace semantic and scale legend construction, final Layout paint/occurrence production, Scene projection, and table-column inputs. Keep key selection and empty-column policy out of Scene; avoid project-specific branches and source-YAML repairs.
2. **Design and normative correction:** settle the open identity, label, witness, and absence/normalization questions; define Layout/model ownership and compatibility/migration effects. Review against Specs06, 07, 08, 28, 33, 49, 60 and 61, plus B #1682. Publish the design, architecture review, and required living-spec correction before finalizing implementation planning.
3. **Implementation planning (later):** split the approved work by owner and public materializer; name focused tests, synthetic fixtures, generated evidence, and publication gates. Do not begin implementation in this planning slice.

## Owners and acceptance evidence to plan

- Likely owners to confirm in design: Layout's completed paint witnesses/composition and table normalization; the pure presentation model's semantic-key composition; Scene/adapters only as projections/materializers. Confirm exact file ownership after the audit.
- Evidence plan must include focused synthetic cases for realized actual/progress paint, all-encoded versus mixed planned marks, absent comparisons and column normalization; a public-example change-count table; and inspected PNGs for the literal acceptance rows. Include conformance and affected public materializers, not Scene-only evidence.
- Open until design review: paint/key identity and labels, absent-versus-empty comparison semantics, exact public examples/artifacts to compare, and migration consequences. Any gap or layer conflict pauses implementation for a published design correction.
