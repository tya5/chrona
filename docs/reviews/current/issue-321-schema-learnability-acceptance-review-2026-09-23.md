# Issue #321 Schema Learnability Acceptance Review

**Scope:** Schema annotations and examples, shared structural diagnostics,
Project v0.6 schedule discrimination, normative reference validation, and the
release gates named in the #321 implementation plan.

**Result:** Accepted.

## Requirement evidence

| Requirement | Evidence |
| --- | --- |
| One deterministic structural explanation at every ingress | `SchemaViolation` is shared only by Core validation and presentation contract parsing. It retains RFC 6901 pointers and expected literals/forms; Core and contracts preserve their public diagnostic adapters. |
| Helpful diagnostics do not cross successful-pipeline boundaries | Import-direction policy permits `schema_diagnostics` only from `core` and `presentation`; View, Layout, Scene, and render packages retain no dependency on it. |
| Every live schema is authorable documentation | Inventory-driven annotation lint passes every `live` schema. It rejects missing descriptions, absent union examples, and examples invalid in their enclosing schema context. The lint now runs in conformance. |
| Clean Project schedule migration | `timeline/v0.6` accepts `fixed-point`, `fixed-span`, `scheduled`, and `rollup`; no v0.5 parser/inventory branch remains. A regression proves removed `mode: fixed` is rejected and reports the four permitted forms. |
| Normative contract drift is prevented | The reference gate derives current values from the live inventory and runs in conformance. Current and historical markers are covered by focused tests. |
| Public behavior remains reproducible | All eight declared public materializer slides reproduce their committed SVG bytes; `git diff --exit-code -- examples/*/generated/*.svg` is empty. |

## Final gates

- Focused schema diagnostics and annotation/reference-gate tests: passed.
- `python conformance/run_conformance.py`: passed.
- Structural checks: module reachability (`63 reachable, 0 staged`), Scene
  primitive delivery (`18` fields), View dispatch (`10` ingress values), and
  import direction (`8 packages, 25 inward edges`) passed.
- `pytest -n 4 -q`: **437 passed, 7 skipped**.
- Wheel build and isolated installed-wheel smoke test: passed.
- All eight public materializer byte checks passed; generated SVG diff was
  empty.

## Architecture conclusion

The implementation keeps structural explanation at ingress, schema reference
metadata at its owning schema, and contract identity in the inventory. It adds
no v0.5 compatibility path and does not move policy into View, Layout, Scene,
or materializers. The new shared-helper import is explicitly constrained to
failure boundaries, so it does not alter the successful Core → View → Layout →
Scene → renderer direction.
