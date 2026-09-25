# Issue #435 boolean table presentation implementation plan

## Governing design

Implement
`docs/design/issue-435-boolean-table-presentation-design-2026-09-26.md` as
accepted by
`docs/reviews/current/issue-435-boolean-table-presentation-architecture-review-2026-09-26.md`.

## I435-1 — View contract replacement and typed ingress

**Files:** `view-v0.20` schema, schema inventory/package-resource mappings,
live View fixtures, `contracts/resources.py`, and focused schema/resource tests.

1. Replace live `view-v0.19` with v0.20 and migrate every live View identity.
2. Represent formatter intent as the finite text-format names or the required
   `presence` object with both declared strings.
3. Parse it into a typed union; reject a known `missingActual` source unless it
   selects that union variant.
4. Add positive/negative tests covering absent, partial, and invalid presence
   declarations.

**Acceptance:** no live v0.19 View remains; raw formatter maps do not cross the
resource boundary; malformed or missing boolean presentation has
`E_VIEW_BOOLEAN_PRESENTATION` before Layout.

## I435-2 — Content normalization closure

**Files:** surface-content formatting, review-content construction, typed
contract/model tests, diagnostic inventory and policy if required.

1. Make boolean formatting exhaustive over the typed presence value and reject
   non-presence bools.
2. Check dynamically resolved boolean fields at review-content normalization.
3. Retain existing semantic-role selection and text metrics input; pass only
   strings into `TableCellContent`.

**Acceptance:** true and false values serialize to their declared strings;
generic `str(bool)` is unreachable; Scene and renderer modules gain no boolean
branch.

## I435-3 — HALCYON evidence and release gate

**Files:** the shared mission-brief View/context identities, generated Scenes
and SVGs, semantic realization report/coverage tests, materializer tests.

1. Migrate the shared `Obs` column to explicit `Missing` / `Recorded` wording.
2. Regenerate all affected public materializers in one batch after I435-1 and
I435-2 are complete.
3. Assert no committed Scene table text is `True` or `False`; assert all three
   gallery slides still satisfy `table-missing-observation` evidence.
4. Run focused tests, public materializer reproduction, schema and inventory
   gates, then the full CI suite as release evidence.

**Publication:** publish source plus generated evidence as one commit; publish
the acceptance review only after CI evidence is available, then close #435.
