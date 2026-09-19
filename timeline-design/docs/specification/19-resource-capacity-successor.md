# Resource, Capacity, and Cost Successor Design

**Status:** Proposed  
**Owns:** successor resource demand, capacity, leveling, and cost boundaries. It does
not change v0.1 Date-only scheduling or make actuals scheduling authority.

## 1. Authority

Project demand declarations are plan inputs. Capacity calendars and assignments are
separately revisioned planning inputs. Actual observations remain independently
revisioned facts and never automatically reschedule a Project. Cost/timesheet entries
are accounting observations, not scheduling constraints.

| Concern | Canonical owner | May affect schedule |
|---|---|---|
| Demand / assignment | Project successor | Yes, when an explicit leveling request selects it |
| Capacity / availability | capacity-set resource | Yes, only as explicit solver input |
| Leveling result | derived evaluation | No; accepted change requires a Command | 
| Actual / timesheet / cost | independent observation set | No automatic effect |

## 2. Resource model

A resource has a stable ID, kind, units, and capacity calendar reference. An assignment
names one Project object, resource ID, demand units, and optional role. Units are
dimensioned quantities; `1 engineer` and `1 machine` are not implicitly comparable.
Resource-specific availability is successor-only and does not redefine v0.1 Calendar.

## 3. Leveling

Leveling is an explicit evaluation request with a declared objective and permitted
movement scope. It returns a proposed derived placement plus overload diagnostics. It
MUST NOT silently write resolved dates, mutate fixed placements, override bounds, or
change a Project merely because capacity is infeasible. Applying a proposal requires a
typed Command against the current base revision; stale proposals reject.

## 4. Cost and timesheets

Cost rates, timesheets, and actual effort are independently identified observations.
Their aggregation is derived and auditable. They may be displayed beside plan demand
but are neither inferred from progress nor used to rewrite capacity or schedule.

## 5. Required evidence before implementation

- schemas/fixtures for units, assignments, capacity calendars, overload, and stale
  leveling proposal rejection;
- Command/Project Format/Quality successor updates and an ADR;
- deterministic solver objective and tie-break rule; and
- review proving that no automatic actual-driven reschedule or hidden leveling write
  exists.
