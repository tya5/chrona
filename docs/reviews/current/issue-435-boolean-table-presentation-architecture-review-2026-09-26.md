# Issue #435 Boolean table presentation architecture review

## Scope reviewed

`docs/design/issue-435-boolean-table-presentation-design-2026-09-26.md`
was reviewed against the live View schema inventory, `ViewInput` resource
parser, review-content normalization, `SurfaceContentInput`, Layout composer,
Scene builder, public Scene schema, and the HALCYON materializer corpus.

## Findings

| Concern | Result | Reason |
| --- | --- | --- |
| Author meaning | Accepted | `whenTrue` / `whenFalse` makes both rendered states explicit and permits an intentional blank. |
| Type safety | Accepted | A tagged typed union prevents an untyped map escaping resource parsing. |
| Dynamic custom fields | Accepted | Normalization checks the resolved value, so schema-static validation is not the only protection. |
| Layer ownership | Accepted | Boolean selection ends before `TableCellContent`; Layout, Scene, and adapters see only text. |
| Schema lifecycle | Accepted | A v0.20 replacement with inventory transition follows the repository's live-contract policy. |
| Icon scope | Accepted | Existing visual capability work is not duplicated by a bespoke table formatter branch. |
| #431 interaction | Accepted | Meaningful words repair #435 without claiming a contrast-policy fix. |

## Required implementation constraints

1. Do not use a default value for the presence pair or accept a partial pair.
2. Do not preserve `format: text` for a known boolean source as a compatibility
   route.
3. Add a negative test for a boolean custom field, not only `missingActual`.
4. Update all live schema/package/inventory references atomically and regenerate
   the public corpus only after the source closure is complete.
5. Keep the realization report's evidence identity intact; changing literal
   text must not make the family unreachable.

## Verdict

Accepted for an implementation plan.  The design strengthens the typed
authoring boundary without widening renderer authority or weakening the
Layout-to-Scene boundary.
