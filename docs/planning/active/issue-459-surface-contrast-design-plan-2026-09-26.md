# Design Plan — Surface-Aware Contrast (#459)

## Published baseline

At `7fceda691fbd839e0d808990830bb6a09a430e36`, #431 provides a
completed-Scene contrast evaluator and a checked public-corpus report. Its
design explicitly assumes the canvas is the ground. #459 reports that this is
false for marks on raised panels and that `variance-behind` is treated as
de-emphasized. The report and issue observations are leads; actual primitive
paint, order, and geometry must be checked before selecting a policy.

Source: [Issue #459](https://github.com/tya5/chrona/issues/459). There are no
later issue comments at planning time. #462 is separately owned and is not a
dependency; do not absorb its design-target work.

## Literal acceptance criteria

1. `variance-behind` text is held to 4.5:1 and meets it on every committed slide.
2. Mark roles have a floor, and every committed planned bar meets it against the surface it is drawn on.
3. The contrast report states, for each primitive, the ground it was measured against.

## Design questions and boundaries

- Identify the complete, finite data-mark role set (planned, actual, snapshot,
  scenario, milestone and related marks) from the semantic registry and Scene
  evidence. Decide which paint channel visibly carries each form.
- Define deterministic ground selection from paint order and actual geometry,
  including raised panels, overlapping bands, transparent paint, strokes,
  non-rectangular marks, and cases where a centre sample is insufficient.
- Keep Theme/Scheme responsible for declared paint; Scene analysis observes
  completed geometry and paint; adapters must not choose a contrast ground.
- Determine whether the 4.5:1 state-text floor applies both at Theme closure
  and to every completed Scene, and migrate affected light-theme declarations
  together with regenerated materializers.
- Check Specification 08, 34, 46, 49 and the #431 design/corrections for
  conflicting ground or role authority; record normative corrections.

## Ordered independently publishable slices

1. Publish this design plan and baseline.
2. Publish the selected design, normative specification correction, and
   whole-architecture review. No product code changes in this slice.
3. Publish an implementation plan covering evaluator/registry, policy and
   Theme migration, generated report and materializers, tests and CI gates.
4. Implement and review each approved slice; publish exact acceptance evidence
   only after the public output and CI are checked.

Evidence must include focused evaluator tests, exhaustive committed-Scene
findings, report regeneration, full public materializer checks, actual SVG
inspection in a batch, and the repository CI matrix.
