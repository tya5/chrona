# Issue #372 — Reverse Report Design Correction Review

**Decision:** Accept correction before implementation continues

## Finding

The initial design said the fenced-command parser would be the sole discovery
source for both execution and reverse CLI-surface validation.  The checked-in
`cli-reference.md` is itself an argparse-generated inline-code report, not an
authored fenced example.  Requiring fenced discovery to prove every option is
documented would either fail every check or require the report to recursively
count itself as an executable document.

## Correction

Split the two evidence forms explicitly:

- fenced authored commands are parsed once, statically grammar-validated, and
  then executed or locally skipped;
- the reverse report is rendered directly from argparse and validated by exact
  generated-file freshness.

This is stronger than allowing an authored example to claim option coverage:
the report necessarily names every live parser surface, while executable
examples prove the selected user journeys actually work.  No product boundary,
CLI grammar, or fixture authority changes.

## Implementation consequence

Do not retain the former `validate_surface()` invocation in the command-line
check path.  Keep its focused helper test only if it remains useful as a pure
report comparison; the authoritative gate is generated-report freshness.
