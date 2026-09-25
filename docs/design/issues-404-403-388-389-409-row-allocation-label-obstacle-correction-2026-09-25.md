# Design Correction — Completed Row Requirements and Label Obstacles (#404, #388)

**Status:** Accepted correction to P1/I2 before row-allocation implementation is accepted.

## Finding

The I2 row requirement initially closed only the physical mark-track stack.
That condition is necessary but not sufficient: plot labels are completed by
Layout after tracks are placed. The existing label request path also removed
*every* mark from its obstacle set whenever the request had an inside host.
Uniform row distribution hid that error. Under `pack`, a label can therefore
be selected over a mark in another row.

## Corrected placement rule

Each label candidate is tested against every completed mark. The sole
exception is the request's declared host mark, and only for that request's
`inside` candidate. A planned/actual comparison sibling is not implicitly a
host. This preserves the existing finite candidate ladder: Layout selects a
non-overlapping alternative or follows the declared suppression/diagnostic
policy; Scene does neither measurement nor collision repair.

Row feasibility remains the physical closure of row minimum, completed mark
tracks, and row padding. It must not predict label text or reserve arbitrary
vertical space: labels are overlay placements whose declared candidate and
overflow policy own their result. The correction makes that overlay policy
actually enforce the completed mark geometry.

## Visible failure boundary

`place_rows` may report its local required and available extents, but the
use-case owns Context-specific remediation language. A Draft may name the
command-line viewport repair. An immutable Context must instead name
`environment.viewport.blockSize` and rematerialization. This preserves #400's
single visible-failure boundary while I2 introduces no new diagnostic code.

## Non-goals

This does not introduce label-quality preferences, table allocation policy,
or renderer behavior. It restores the invariant that Layout never emits a
non-inside label over a completed mark.
