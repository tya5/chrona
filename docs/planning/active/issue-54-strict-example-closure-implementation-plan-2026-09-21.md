# Issue #54 opt-in closure implementation plan

## Preconditions

The #44-aligned correction specification, ADR-0030, and cross-boundary review are published.

## I54-1

Remove unconditional `--require-content-identity` from the public materializer command.
Do not change the byte-copy or supplied-pin verification path.

## I54-2

Update materializer tests to prove:

- unpinned Controller Z, HALCYON, and ASTER contexts reproduce;
- a supplied wrong resource pin rejects in check and write mode without changing SVG;
- a supplied wrong font pin rejects with `E_MATERIALIZER_FONT_IDENTITY`;
- authored context bytes remain unchanged.

## I54-3

Run the complete external gate on the new main SHA: focused tests, all five manifest
check-mode executions, acceptance contexts, and full pytest. Record results on #52/#54,
then close #49 only if all recovery requirements are green.
