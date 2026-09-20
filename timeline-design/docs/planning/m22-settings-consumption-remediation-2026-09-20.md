# M22 Settings-consumption remediation plan — 2026-09-20

**Status:** I24-1 published; D24 placement/status addendum complete and awaiting publication
**Scope:** GitHub issues 11–12 and PR 13, evaluated against `main` at `9be3712`
**Exclusion:** M23 observation tables and milestone digests remain deferred

## 1. Findings

Issue 11 is valid on the common Scene path: the Rect contract has no corner-radius
payload, so `theme.bar.radius` cannot reach SVG without violating Scene ownership. The
legacy `data-stack` hook also disappeared even though Scene already owns stable lane
assignments.

Issue 12 is mixed. It found real gaps, but its `116/176` count came from `821edb3` and
one Controller Z rendering. I3 subsequently implemented axis formats, point/arrow
shape, opacity, and Actual height. Other reported leaves are correctly conditional:
point shape requires a point; missing pattern requires missing Actual; summary and note
typography require those slots; default facet paint requires absence of a group
override. A byte-identical mutation outside its trigger is not a defect.

PR 13 is not merged unchanged. Its perturbation engine is retained as a useful test
mechanism, but `KNOWN_INERT` is replaced by the versioned conditional consumption
matrix. A matrix row is a contract, not an allow-list of accepted defects.

## 2. Closed design decisions

1. `settings.layout` is the sole layout authority on the v0.2 common-Scene path. A
   v0.1 Layout Profile participates only in the explicit legacy adapter.
2. Every setting is `unconditional`, `conditional`, `validation-only`, or `superseded`.
   Conditional rows name a fixture trigger and an owned Scene/SVG observer.
3. Rect `cornerRadius`, comparison-mark `laneGroupId`, and `stackIndex` are completed
   Scene data. SVG serializes them without consulting authoring settings.
4. Stroke purpose selects one complete Theme stroke token: color, opacity, width, and
   dash are not independently recovered.
5. Missing Actual and variance markers are explicit Scene primitive families; neither
   changes Project, Schedule, or Actual authority.
6. Required label rules diagnose placement failure. Optional rules may follow the
   declared optional-overflow policy; omission is observable and not silently promoted.
7. `variance.visible=false` suppresses variance marker/label primitives and
   `routing.enabled=false` suppresses connector/leader/explanatory-path families.
8. Existing schema fields that remain behavioral are implemented rather than silently
   accepted. Removal requires a future versioned schema decision, not this remediation.

## 3. Execution phases

| Phase | Work | Exit evidence |
|---|---|---|
| D24 | Publish this plan, owning specification changes, Scene fixture, matrix schema/fixture/validator, ledger and design review. | Design validators and full conformance pass; no product implementation change. |
| I24-1 | Scene Rect radius and mark stack metadata; purpose-complete stroke serialization. | Radius/minWidth/data-stack and stroke token tests; #11 reproduction passes. |
| I24-2 | Variance status/marker, missing-Actual pattern/label, annotation paint, group/default facet coverage. | One trigger fixture per conditional family; owned property changes. |
| I24-3 | Required label behavior plus variance/routing visibility; conditional typography and layout coverage. | Required/optional diagnostic tests and matrix rows all have observers. |
| I24-4 | Replace PR 13's allow-list oracle with matrix-driven perturbation and targeted fixtures. | No known-inert allow-list; every matrix row is exercised or validation-only. |
| A24 | Regenerate artifacts, visual review, full regression/conformance, reconcile issues/PR, and return M22 to Complete. | Published SHA equals verified local state. |

Progress: D24 is complete. I24-1 is complete locally with 209 tests and full
conformance passing and is published at `f39e25e`. The pre-I24-2 review found that the
original design named four variance roles without closing the unknown trigger or exact
marker/label geometry. Implementation paused. The following D24 addendum closes those
choices before I24-2 resumes.

### D24 addendum: conditional-family geometry

- Missing Actual applies to spans whose Actual mapping lacks either required endpoint.
  Its three modes emit only the named label/pattern families, using the planned left
  edge and resolved Actual band defined in specification 08.
- Known variance status is the sign of the calendar-day actual-finish minus planned-end
  delta. A non-empty partial Actual mapping is `variance-unknown`; an absent mapping is
  not a variance observation.
- Variance offset, marker width, label gap, label alignment, and formatted label text
  have the exact ownership and geometry rules in specification 08.
- Conditional labels use their declared preferred x, then shift left as one measured
  box at the viewport's right margin. This keeps valid right-edge schedules visible
  without changing dates or truncating text; a label wider than the margin box is a
  required-overflow diagnostic.
- This addendum changes no schema, semantic Project/Actual authority, or phase order.

Each implementation phase is independently tested and published. Any new semantic
choice stops implementation and reopens D24 before code continues.

## 4. Acceptance boundaries

- No sample, preset, title, group ID, or object ID branch.
- No adapter date/placement/stack/radius reconstruction.
- No output-byte assertion without a named trigger and owned-property observer.
- Conditional absence is permitted only when recorded in the matrix.
- Legacy SVG behavior is not evidence for v0.2 completion.
- M23 remains excluded.

I24-2 is published at `7915501`: the four variance statuses, marker width, missing-Actual
mode/pattern, annotation fill/stroke/leader paints, and existing group/default facet
fallbacks have targeted observers. The ASTER artifacts were regenerated without SVG
overflow.

The I24-3 pre-implementation review reopened D24 before code. Specification 08 now
closes next-finer minor tick generation and maps every label-rule source to its Scene
family, including applicability, duplicate precedence, and required/optional failure
behavior. I24-3 resumes only after this addendum is published and tree-verified.

I24-3 is complete locally with targeted observers for minor strokes, date/title label
rules, required versus optional omission, variance/routing visibility, and optional
typography families. The five ASTER artifacts were regenerated with zero SVG overflow;
214 tests and full conformance passed, and I24-3 is published at `fac5fb8`.

The I24-4 pre-review reopened D24 for the final unresolved Output behavior.
Specification 08 now defines `ScenePrimitive.optional`, exact coordinate rounding,
reference-only SVG font capability, and whole-primitive optional overflow omission.
I24-4 resumes only after this addendum is published and tree-verified.

I24-4 is complete locally. SVG consumes all Output fields, optionality is explicit
Scene data, and the matrix-driven test rejects every unresolved disposition across all
24 rows. There is no exact-path `KNOWN_INERT` allow-list. Targeted behavioral tests
remain the observers named by the matrix.
