# Integrated Surface Quality Programme Plan (#404, #403, #388, #389, #409, #405, #406, #407, #408, #400, #414, #402, #413, #410, #412, #411)

**Status:** Active planning. No implementation is authorized by this plan.

## Purpose

The sixteen issues are evidence of five connected product boundaries, not a
queue of renderer patches. This programme delivers them in an order that keeps
semantic authority, View intent, Layout geometry, completed Scene values, and
adapter projection separate:

```text
P0 evidence refresh
  -> P1 hierarchy and table--timeline composition
  -> P2 axis and visible-failure policy
  -> P3 semantic-to-visual realization
  -> P4 typography, orientation, and draft font provenance
```

Each programme follows the required sequence independently: design plan,
English design, cross-architecture review, implementation plan, implementation,
acceptance/release review, then serial publication. A discovered mismatch
returns to its programme's design; it is not repaired in Scene or an adapter.

## Verified starting point

* `main` is `deb74e7bb8a66aa042d18a1880af791121744619` and equals
  `origin/main` at planning time.
* View v0.15 still gives table columns content/missing-value declarations but
  no column geometry or alignment; Layout's table/timeline composition is the
  only owner of their coordinates.
* The current axis composition derives band and label levels by array position;
  `axis_intervals(..., tick_step=...)` and `fitting_axis(requested="auto", ...)`
  exist but are not fully represented by the View contract.
* Specifications 02, 24, 33, 36, 50, 55, 63, and 64 remain the governing
  boundaries. In particular, project hierarchy is semantic structure and View
  grouping is not semantic hierarchy.
* #394, #395, #396, #397, #398, #399, and #401 are closed. The measurements in
  #414 and portions of #408/#413 that were taken before those releases are not
  current acceptance evidence.

## P0 -- Current evidence and issue normalization

Before changing a contract, rerun every numerical and structural claim in the
sixteen issues against the current public corpus and code. Publish a compact
disposition table that records, per claim, one of `still-open`, `already-closed`,
`superseded`, or `requires-design-decision`, with the exact command/source used.

This is not a replacement for the presentation-coverage report. It prevents a
historical count from creating duplicate capability or from re-opening a
completed boundary. #414 becomes the long-lived measurement/triage issue only
after its closed relation, icon, actual, and locale rows are removed.

**Acceptance:** the later designs cite current evidence only; no implementation
unit claims #414 coverage from an obsolete corpus count.

## P1 -- Hierarchy and table--timeline composition

**Issues:** #404, #403, #388, #389, #409.

### Design order

1. **Hierarchy contract (#404).** Define the distinct meanings and permitted
   combinations of Project parent/child hierarchy, View `grouping.by:
   hierarchy`, explicit Review-row depth, and WBS/path columns. A View must
   name the column that renders hierarchy indentation; position zero is never
   semantic authority. Decide whether conflicting duplicate hierarchy
   declarations are normalized, composed, or diagnosed.
2. **Measured table/row composition (#403, #388).** Define column
   presentation as View intent (alignment, width allocation, header grouping
   only if admitted) and have Layout measure and allocate it. Define each row's
   required block extent from its completed marks plus declared padding, then
   derive the surface requirement from the sum of rows and group headers.
   Surplus distribution is a finite Layout Profile policy, not implicit equal
   division. This design must use the existing placement/overflow contract;
   View never carries pixels and Theme never chooses a row's allocation.
3. **Cross-slot decorations (#389, #409).** Define a Layout-owned decoration
   layer spanning the table and timeline review surface. View/Theme may select
   a finite alternation and role treatment; Layout emits completed rectangles
   and Scene only projects them. Establish a single background-channel policy:
   overlapping translucent fills are prohibited by the shipped-theme gate;
   one signal must use a non-fill treatment or a non-overlapping region. Paint
   order is an explicit completed Scene value, not builder emission order.

### P1 acceptance

* hierarchy, group semantics, WBS/path, and explicit depth have one documented
  interaction contract and rejecting cases have stable diagnostics;
* a named hierarchy column, numeric alignment, and deterministic measured
  widths work without layout inference in Scene;
* row height depends on its own completed content and declared policy, and
  immutable/draft overflow retains the existing distinct path guarantees;
* row/group/calendar decoration can span the complete review row and shipped
  themes cannot compound translucent background fills;
* corpus fixtures, placement invariants, public materializer bytes, generated
  SVG review, full pytest, wheel smoke, and three-platform CI pass.

## P2 -- Axis contract and visible-failure policy

**Issues:** #405, #406, #407, #408, #400.

P2 starts only after P1's row and background composition contracts are stable,
because axis labels and calendar decoration share the same completed surface.

The design replaces positional level interpretation with typed per-tier intent:
unit, label vocabulary valid for that unit, tick frequency or automatic fitting,
band/grid participation, alignment, and declared overflow behavior. It decides
half-year and calendar-derived fiscal offset as calendar facts, not ad-hoc label
formatting. Project-relative weeks require a separately declared semantic
origin and are either designed explicitly or recorded as deliberately absent.

Locale selects a declared name table, never an implicit vocabulary. The current
finite locale boundary remains intact. A year/week declaration must either
change output or be rejected; no required dead property survives migration.

P2 also publishes the general failure taxonomy proposed by #400. A failure
that silently loses reader information must diagnose or create an explicit
visible substitute/record. A visible geometry degradation follows its
slot/path policy and is never overridden by an unconditional helper raise.
The taxonomy governs P1's row overflow but does not move its allocation logic
out of Layout.

**P2 acceptance:** every accepted tier is consumed exactly once; auto and
every-N are reachable; label suppression is observable; fiscal/half-year
behavior is calendar-consistent; and tests cover all policy branches through
the public View contract rather than helper-only calls.

## P3 -- Semantic distinctions realized visually

**Issues:** #414, #402, #413.

P3 first publishes a schema- and corpus-derived realization report. It compares
the cardinality of admitted semantic states with completed Scene visual roles,
without treating every state difference as an automatic demand for a new role.
Every intentionally shared treatment needs an explicit reason in the report.

Then it implements only the confirmed gaps:

* table cells receive a state role from the already-projected fact when their
  declared source admits one, otherwise retain their column role;
* annotation purpose resolves independently to box, leader, and text semantic
  roles; purpose-specific leader terminal intent is projected through the
  completed relation/marker mechanism rather than recreated in SVG.

Annotation routing policy remains separate from dependency routing. This
programme consumes the closed relation-marker and annotation-text contracts;
it does not resurrect pre-release alternatives.

**P3 acceptance:** the report is deterministic and current; a role distinction
is traceable from semantic input through Layout placement and Scene to public
output; table and annotation corpus evidence demonstrate the admitted states;
and deliberate equivalences are documented.

## P4 -- Typography, orientation, and draft font provenance

**Issues:** #410, #412, #411.

P4 begins after P1/P2 establish their consumers, so typography is not added as
adapter decoration. Its design treats letter spacing, transform, numeric
spacing, and orientation as `TextLayout`/FontMetrics inputs. The exact text
used for measurement is the text painted by every adapter; orientation swaps
the measured occupied axes before fit/overflow decisions.

The design must make an explicit product decision for `writingMode`: either
narrow it to the behavior actually supported, or define its axis-assignment
semantics separately from optional rotated horizontal runs. It must not claim
CJK vertical composition from a 90-degree label transform.

System fonts, if admitted, are draft-only provenance-bearing inputs. Resolution
selects one actual local font file and reads its metrics; missing family is a
diagnostic; immutable Context/materialization/review paths reject a closure
containing a system-font provider. No host fallback, font substitution, or
adapter-only system lookup is allowed. Packaging a new default font requires a
licensing and wheel-size gate, not an incidental fixture asset.

**P4 acceptance:** typography and orientation have matching measurement and
paint evidence; draft system-font use is explicit and immutable use refuses;
all font identities are visible in closure evidence; and native, SVG, and PNG
tests prove the same resolved text geometry.

## Publication and verification protocol

For every design, implementation-plan, implementation, and review publication:

1. run focused validation for that artifact and inspect generated changes;
2. `git fetch origin main`, compare the exact range with `origin/main`, and
   push fast-forward only;
3. verify the GitHub commit/PR/merge state before starting the next phase;
4. for an implementation release, batch expensive checks once per accepted
   programme: focused tests, full pytest, structural/coverage gates, all
   affected public materializers, one generated-SVG diff review, installed
   wheel smoke, and GitHub three-platform CI.

No compatibility reader is added solely to preserve a superseded presentation
contract. Migration impact and removal are stated in the relevant design.

## Completion audit

The programme is complete only when every named issue is closed with public
design, implementation, and acceptance evidence; the P0 disposition table has
no unaddressed claim; all new contracts have corpus realizations; and the
cross-programme review confirms the ownership chain remains:

```text
Project / Actual / Calendar facts
  -> View semantic and presentation intent
  -> Theme and Layout completed treatment/geometry
  -> Scene completed target-neutral primitives
  -> adapter projection
```
