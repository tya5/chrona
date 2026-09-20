# I0 Core Issue Remediation Review

**Conclusion:** Accepted. The implementation conforms to the published issue
remediation design without widening Core v0.1 semantics.

## Evidence

- Project-order scheduling is independent of `PYTHONHASHSEED` values 1–5.
- Invalid point/span endpoints diagnose `E_ENDPOINT_MODE_MISMATCH` during validation
  and do not escape as `KeyError`.
- Composite relation lags detect every `wd` component and use the declared calendar.
- An explicit anchor conflicting with the opposite endpoint lower bound diagnoses
  `E_CONTRADICTORY_BOUNDS` and produces no empty placement.
- An end lower bound is retreated by the amount before it is combined with start lower
  bounds.
- Empty working-day calendars fail schema validation, and non-working explicit
  WorkPeriod start anchors diagnose `E_NON_WORKING_ANCHOR`.
- The original v0.1 extension string remains schema-readable while reproducible
  evaluation requires migration to an immutable reference.

The focused remediation suite passes 19 tests. The complete suite passes 187 tests
with two existing `jsonschema.RefResolver` deprecation warnings. The complete
conformance runner passes.
