# Design — Visible Row-Density Policy Completion (#400)

**Status:** proposed for architecture review.

## Decision

Row density is a physical surface-capacity policy, not text overflow.  Layout
Profile v0.9 will replace v0.8 and require a finite `reviewSurface.rowDensity`
declaration:

```yaml
rowDensity:
  draft: compact-with-warning
  immutable: diagnose
```

The only values are `diagnose` and `compact-with-warning`.  This avoids
misusing `ellipsize-with-source` or generic slot `clip-optional`, whose
semantics concern a single text/slot content item rather than a coordinated
table-timeline row and its marks.  Every shipped profile migrates explicitly;
v0.8 has no live reader.

## Failure registry

Layout owns a finite `FailureDisposition` registry.  Each outcome contains a
failure kind, visibility class, policy, and structured details.  The initial
registry contains:

| Failure | Visibility | Existing/selected disposition |
| --- | --- | --- |
| axis label non-fit | invisible loss | diagnose or recorded thinning |
| relation route suppression | invisible loss | recorded suppression warning |
| table text overflow | visible degradation with retained source | declared table ellipsis policy |
| row density | visible degradation | `rowDensity` policy |
| mark containment under ordinary rows | correctness invariant | diagnose |

The ordinary mark-containment invariant remains unchanged.  Only the selected
row-density path can introduce an explicit clip region; it is not a global
relaxation of `E_LAYOUT_MARK_OVERFLOW`.

## Row-density geometry

P1 remains the sole authority for uncompressed row requirements.  Given
available timeline block extent `A` after group headers and required row
extents `R[i]`:

* if `A >= sum(R)`, normal `pack|fill` placement is unchanged;
* if `A < sum(R)` and policy is `diagnose`, Layout returns
  `E_LAYOUT_REQUIRED_OVERFLOW` with required/available details;
* if `A < sum(R)` and policy is `compact-with-warning`, Layout allocates each
  row proportionally: `H[i] = A * R[i] / sum(R)`, in stable review-row order.

Rows, table cells, and marks retain their ordinary completed geometry but each
gets a Layout-created physical row clip host.  Text and marks reference that
host through completed placement data.  Thus a dense output visibly clips at
row boundaries rather than silently dropping an object, drawing outside its
row, or letting an adapter invent a crop.  The clipped fraction is an
intentional, observable degradation.  Layout emits one `W_LAYOUT_ROW_DENSITY`
outcome containing required/available extent, policy, and affected row IDs.

The policy does not scale fonts, synthesize marks, merge rows, change source
selection, or alter the P1 requirement calculation.  A completely non-visible
mark still has a retained completed placement and a clip reference; it is
therefore inspectable rather than silently absent.

## Path resolution and transport

Draft and immutable mode are explicit `LayoutRequest` inputs derived from the
closure revision, not renderer behavior.  A draft with `WIDTHxauto` still
grows to P1 requirement before the policy is considered.  A fixed-height
draft uses `rowDensity.draft`; immutable materialization uses
`rowDensity.immutable`.  This makes the author-visible draft default and the
evidence default reproducible profile data rather than a hidden use-case
exception.

`RowDensityOutcome` belongs to the Layout placement closure and is projected
as completed surface diagnostics and clip references.  Draft CLI renders emit
the structured warning on stderr.  Inspection Scene serializes the completed
outcome but no host/adapter policy.  SVG/PNG/PDF/typeset serialize supplied
clip geometry only; none decides whether a row is dense or what to omit.

## Migration and acceptance

All current Layout Profiles migrate together to v0.9 with the shown
draft/immutable default.  A purpose-built profile and corpus Context exercise
both `compact-with-warning` and `diagnose`; public materializers retain
diagnosis unless their profile explicitly opts into compaction.

Acceptance requires: a fixed-height draft with insufficient rows renders and
emits `W_LAYOUT_ROW_DENSITY`; an immutable `diagnose` profile fails; an
immutable explicitly compact profile has clip-hosted completed placements;
ordinary mark-containment negatives still fail; no Scene/adapter computes row
policy; all public materializers, full tests, conformance, visual review, and
three-platform CI pass.
