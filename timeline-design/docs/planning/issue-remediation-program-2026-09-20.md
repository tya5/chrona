# Issue Remediation Program — 2026-09-20

**Status:** Design complete; implementation authorized in the phases below  
**Scope:** GitHub issues 1–10 reviewed against `main` at `e9c64e4`  
**Exclusion:** M23 review-detail surfaces remain deferred

## 1. Purpose

This program repairs accepted product contracts that were found incomplete after their
milestones had been marked complete. It is remediation of M0, M1, M5, and M22 evidence,
not a new presentation feature milestone and not authorization to implement deferred
M23 observation or milestone panels.

Every phase follows this order: update the owning design, validate it, publish it,
implement only that design, run inherited and phase-specific evidence, publish one
non-force commit, and verify the published SHA before the next phase. GitHub writes are
strictly serial.

## 2. Current issue disposition

| Issue | Current disposition | Owning contract |
|---|---|---|
| #1 | Valid: schedule result ordering varies with process hash seed. | Scheduling 04; Quality 12 |
| #2 | Valid: endpoint/mode mismatch and composite WorkPeriod lag can escape as exceptions. | Project Format 05; Scheduling 04 |
| #3 | Valid: a start anchor can be silently replaced by an end lower bound. | Scheduling 04 |
| #4 | Valid for the explicit legacy adapter. | Scene 08; Presentation Settings 29 |
| #5 | Valid repository-authority and version-compatibility defect. | Manifest; Project Format 05; this program |
| #6 | Valid: host font discovery is not an immutable asset resolver. | Application 09; Presentation Settings 29 |
| #7 | Split: CLI, documentation, empty-calendar, non-working-anchor, and conformance items are valid; source modules are not classified as orphaned merely because the CLI does not import them. | 04, 05, 09, 12 |
| #8 | Valid: declared axis formats are unconsumed; year-less labels and year bands require a closed design. | 08, 29, 30 |
| #9 | Partly valid: point size is consumed by the common Scene path; point and arrow shapes are not. | 08, 29, 30 |
| #10 | Primary defect resolved by the common Scene path; add regression evidence. Facet opacity remains valid separate work. | 07, 08, 29 |

## 3. Closed Core scheduling decisions

### 3.1 Deterministic order

The reference scheduler evaluates ready objects in Project document order. It returns
placements in that same Project object order, regardless of whether an object was
fixed, immediately ready, or resolved in a later pass. Diagnostics over multiple
objects use the same stable order. No set iteration order is externally visible.

### 3.2 Endpoint compatibility

A fixed point exposes only `at`. A fixed span and a scheduled span expose only
`start` and `end`. Every dependency source and target endpoint is checked against the
referenced object's exposed endpoint set before scheduling. A mismatch is a semantic
validation failure with `E_ENDPOINT_MODE_MISMATCH`; scheduler internals also degrade an
unexpected endpoint into that diagnostic rather than raising `KeyError`.

### 3.3 Temporal amount calendar requirement

Whether an amount needs a working calendar is derived from parsed amount components.
Any `wd` component requires a calendar, even when it is not the final component.
Suffix tests are prohibited for schedule amounts and relation lags.

### 3.4 Bounds and anchors

An explicit anchor remains authoritative. If any lower bound on either endpoint would
require moving the anchor or its derived opposite endpoint, scheduling returns
`E_CONTRADICTORY_BOUNDS` at the anchor. Without an anchor, an end lower bound contributes
`retreat(endBound, amount)` as a start candidate; it never becomes a start date itself.
The chosen start is the maximum of all start candidates, followed by the already
specified target-calendar normalization.

An explicit WorkPeriod start anchor must itself be working. A non-working explicit
anchor returns `E_NON_WORKING_ANCHOR`; it is never normalized. A calendar with no
working weekdays is structurally invalid and is rejected at its `working_days` field.

## 4. Closed repository and CLI decisions

`timeline-design/` is the living, versioned Chrona specification set. Git history
preserves earlier candidates; the current directory is not a byte-for-byte frozen
import. The manifest points to current authoritative paths and validation attestations
name their exact validation scope.

The original `timeline/v0.1` extension string form remains schema-readable for backward
compatibility, but reproducible evaluation of that legacy form reports
`E_PACKAGE_RESOLUTION_REQUIRED`. Immutable object references remain the executable form.

CLI read commands support exactly two explicit modes: a raw path documented as Draft
evaluation; or `--snapshot-reference`, `--snapshot-root`, and `--store-identity`
together, resolved through `LocalSnapshotReader` with no path fallback.

`render` accepts optional resolved `--presentation-settings`. Without it, output remains
the explicit diagnostic legacy adapter. The legacy adapter keeps a separate label
gutter, non-overlapping heading, and muted ten-pixel tick labels, but does not acquire
v0.2 reproducibility claims.

## 5. Closed font-metrics decision

Font measurement consumes an explicitly declared, content-addressed metrics table, not
a family lookup or font file selected from the host. Each `fontMetrics.assets` entry
gains a required `path` to a `chrona/font-metrics/v1` JSON resource relative to an
explicit asset root. The table owns family, weight, units-per-em, ascent, descent,
default advance, and Unicode-codepoint advances. Its canonical file bytes are verified
against `contentIdentity`; its family and weight must match the declaration.

Resolution rejects absolute paths, traversal, missing files, malformed tables,
content-identity mismatch, family mismatch, or weight mismatch with
`E_FONT_METRICS_UNAVAILABLE`. `fc-match`, TrueType collection selection, and direct
font-file opening are removed from the product path and tests. The repository may check
in generated metrics tables without redistributing font outlines; the table revision
records its source and generation contract.

## 6. Closed presentation decisions

Axis interval facts and display formatting remain separate. The axis module returns the
natural bucket and the Scene formatter applies the closed Detail format using explicit
Context locale. Existing month formats and quarter formats must all produce their
declared spellings. Add `short-month`, `long-month`, `numeric-month`, and `quarter`.
A `year` axis level displays a four-digit year and uses the `year` typography role.

Scene `Symbol.shape` is the resolved Theme point shape. The SVG adapter serializes
diamond, circle, and square from the same bounds used for ports and legends. Arrow
shape is triangle, chevron, or none; `none` omits both marker definition use and
`marker-end`. Facet paints apply both color and declared opacity to marks. Planned and
Actual heights are independently consumed from the Theme.

Settings coverage is a conditional consumption matrix, not a rule that every leaf must
change every rendering. Each declared setting has at least one fixture in which changing
it changes the owned Scene or SVG property, or an explicit validation-only
classification.

## 7. Implementation and publication phases

| Phase | Work | Exit evidence |
|---|---|---|
| D0 | Publish this program, owning-spec changes, manifest/readme correction, and ADR renumbering. | Design validators and link/path audit pass. |
| I0 | #1–#3 plus #7 calendar/anchor fixes. | Reproductions become diagnostics; hash-seed outputs match; full suite passes. |
| I1 | Snapshot CLI mode, v0.2 render option, legacy layout, help and docs. | Raw and pinned CLI fixtures; controller-x regression; full suite. |
| I2 | Exact font-metrics table resolver and Linux/macOS CI. | No `fc-match` or font-file opening; identity/family/weight tests; full suite. |
| I3 | Axis formats/year, point/arrow shapes, opacity, actual-height evidence. | Settings consumption tests, visual artifacts, full suite. |
| R0 | Full conformance, acceptance review, issue evidence and closure. | Published SHA equals verified local state. |

Implementation stops whenever it discovers an unowned semantic choice. The choice is
first added to this program and its owning specification, validated, and published;
only then may implementation resume.
