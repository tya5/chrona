# Core v0.1 Diagnostics

**Status:** Proposed

Diagnostic identifiers are part of the conformance surface. Human-readable wording is
not normative.

| ID | Meaning |
|---|---|
| `E_SCHEMA` | Project does not satisfy structural schema |
| `E_REFERENCE` | Referenced object/calendar/profile cannot be resolved |
| `E_TEMPORAL_TYPE` | Incompatible temporal coordinate or amount type |
| `E_INVALID_SPAN` | Resolved or fixed span is empty or reversed |
| `E_INVALID_AMOUNT` | Amount is invalid for the requested scheduling role |
| `E_CALENDAR_REQUIRED` | WorkPeriod requires a calendar but none resolves |
| `E_CONTRADICTORY_BOUNDS` | Lower/upper bounds cannot be simultaneously satisfied |
| `E_ENDPOINT_MODE_MISMATCH` | A relation endpoint is unavailable on the referenced point/span placement kind |
| `E_NON_WORKING_ANCHOR` | An explicit WorkPeriod start anchor is not a working date in its calendar |
| `E_UNSATISFIABLE_DEPENDENCIES` | Dependency system has no feasible solution |
| `E_UNSUPPORTED_CYCLE` | Implementation supports only an acyclic subset |
| `E_FIXED_TARGET_VIOLATION` | A bound/dependency conflicts with authoritative fixed placement |
| `E_DERIVATION` | Derived placement cannot be resolved |
| `W_NEGATIVE_LAG` | Dependency uses negative lag |
| `W_DEADLINE` | Resolved schedule violates a deadline |
| `W_SUMMARY_DEPENDENCY` | Dependency targets or sources a derived summary object |

Implementations MAY add diagnostics but MUST NOT reuse these identifiers for different
meanings.
