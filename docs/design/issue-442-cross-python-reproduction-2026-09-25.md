# Design — Cross-Python Public Evidence Reproduction (#442)

**Status:** accepted for implementation planning.
**Implements:** `issue-442-cross-python-reproduction-design-plan-2026-09-25.md`.

## Decision

Completed Layout geometry has one determinism boundary: finite float
accumulations that affect placement use `math.fsum` through a local
`geometry_sum` helper.  The helper is owned by Layout, accepts float fragments
(and exact integer fractions from typed allocation declarations), and returns
its correctly rounded float result.  It does not round, quantize, serialize,
or accept `Decimal` values.  `Rect` continues
to own its existing Decimal conversion after a completed float coordinate is
selected.

This solves the cause rather than hiding it: Python 3.11 and 3.12 differ in
the builtin `sum` algorithm for floats, while `math.fsum` defines the same
correctly rounded result on both supported interpreters.

## Numeric classification and ownership

| Class | Policy | Current relevant sites |
| --- | --- | --- |
| Float geometry | must use `geometry_sum` | table minima/preferred/base allocation; row required extent; dependency-network extent comparison; route length; completed icon/annotation/note visual advances; source text block size; group requirement aggregation |
| Decimal geometry | builtin `sum(..., Decimal(0))` remains valid | layout engine allocation, grid span, flow and measured-source aggregates; dependency-network cross-size aggregate |
| Integer/count | builtin `sum` remains valid | semantic counts, boolean count constraints, track count |
| Non-placement limits | builtin `sum` remains valid | normalized icon command-count limit |

The implementation must re-audit every `sum(` below
`src/chrona/presentation/`; this table is a classification contract, not a
permission to leave an unreviewed call site.

`geometry_sum` resides in Layout's numeric model module rather than Scene,
renderers, contracts, or the materializer.  Layout already owns completed
coordinates and is the only layer permitted to choose a numeric accumulation
policy for them.  Scene transports completed coordinates; adapters serialize
them and do not repair numeric drift.

## Structural invariant

No direct builtin `sum` may consume float geometry in a Layout placement path.
A repository structural test inspects the approved Layout modules and permits
only:

* calls to `geometry_sum` for float placement data;
* builtin sums with an explicit Decimal start value; and
* builtin sums whose expression is statically a count/boolean or whose module
  is listed in the reviewed non-placement allowlist.

The check intentionally fails closed for an unclassified new Layout `sum`.
It does not attempt to police generic Python numerics outside presentation.

## Evidence and CI

The public generated corpus is regenerated in full after all float placement
paths use the helper.  The rewrite is expected to change only coordinates
whose historical result depended on builtin accumulation, plus the planned
#412 contract/provenance changes; it must not add a serializer rounding rule.

The existing `conformance` matrix remains cross-platform on Python 3.11.
A separate Ubuntu `reproduction` job uses Python 3.12 (the current newest
supported minor) and runs the public corpus materializer reproduction test.
Thus the lowest supported minor and newest supported minor each prove every
committed slide byte-for-byte.  Maintaining platform coverage separately
avoids multiplying the full wheel/conformance matrix without losing the
cross-minor evidence property.

Interpreter identity is deliberately not added to immutable Scene provenance:
it would encode an implementation accident into a portable evidence contract
and normalize two different outputs.  Nor is `--write` restricted by an
environment heuristic.  The deterministic arithmetic invariant plus the CI
minor matrix makes evidence valid independent of the machine that writes it.

## Interaction with #412

#412 continues to own orientation ingress, completed rotation geometry, and
Scene v0.5.  #442 owns only deterministic arithmetic and its release evidence.
The generated Scene is immutable evidence of both the View/Profile inputs and
the Layout arithmetic.  Because #412's required v0.5 contract migration has
already changed those inputs, there is no materializable public corpus state
in which #442 can regenerate only its arithmetic evidence while leaving #412's
new provenance and required text fields unpublished.

Therefore the two implementation streams have one **atomic public release**:
#442's helper, structural gate, dual-minor workflow, and complete regenerated
corpus publish with #412's View/Profile/Scene v0.5 contract, adapters, and
same corpus.  This changes publication grouping only; it does not merge their
ownership.  No orientation field, transform, or adapter gains Python-version-
specific behavior.

## Acceptance criteria

1. Every classified float accumulation that can influence a completed
   placement uses `geometry_sum`; a structural test rejects a new unclassified
   direct builtin float sum in Layout.
2. Decimal and count sums retain their original numeric domains and behavior.
3. All 21 committed public slides reproduce byte-identically on Python 3.11
   and Python 3.12.
4. CI proves the existing cross-platform 3.11 gate and the complete Ubuntu
   3.12 public corpus reproduction gate.
5. Generated evidence contains no interpreter-specific provenance or rounding
   workaround, and Scene/adapters remain numeric-policy-free.
