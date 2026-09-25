# Relation semantics implementation plan (#394, #395)

## R1 — Typed fact and current contracts

Add Theme v0.9 and View v0.15, normalize relation content selection, and
project typed relation facts including endpoint, lag, calendar and semantic
class. Remove live ingestion of the superseded contracts; retain transition
inventory evidence only.

Acceptance: schema/normalizer tests reject invalid terminal/content forms and
prove signed calendar-qualified lag reaches the typed projection.

## R2 — Completed terminal and label placement

Extend completed relation placement with independent endpoints. Route from the
typed fact, create source/target marker geometry, and use the shared label
candidate/collision machinery for selected relation content and existing
overflow policy.

Acceptance: structural tests prove Scene and adapter do not route/measure;
neutral fixtures cover source marker, circle terminal, zero-lag omission,
suppression, and diagnose.

## R3 — Scene/adapters and evidence

Publish Scene v0.4 with `markerStart`/`markerEnd`; remove the singular field;
adapt SVG and all inspection consumers. Add corpus View/Theme evidence for
start-to-start, positive calendar lag and negative lag; regenerate all public
materializer outputs and coverage reports.

## R4 — Release review

Run focused tests, full pytest, conformance, delivery/reachability/coverage
checks, public materializer bytes, generated SVG review, wheel smoke, and
three-platform CI. Publish acceptance review, then close #394 and #395.
