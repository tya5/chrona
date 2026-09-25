# Design Correction — Preserve Single Schema Diagnostic Semantics (#450)

The initial #450 design incorrectly said `explain_errors` could become the
first member of `explain_all_errors`.  Existing union diagnostics deliberately
summarize legal forms at the wrapper; flattening them changes the public
single-error message.  Correct decision: `explain_errors` remains byte-for-byte
unchanged.  `explain_all_errors` is a new aggregation API that flattens union
wrappers only for multi-diagnostic collection.  The collector selects the new
API; all existing single-error callers retain the existing API.
