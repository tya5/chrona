# #257 Public Schedule Analysis Architecture Review

**Result:** Accepted for implementation.

The Scheduler already owns criticality and float; the public CLI is its proper
outward adapter.  Serializing completed analysis keeps scheduling semantics
upstream of presentation.  A View may consume the same facts independently,
but neither View nor CLI becomes the authority that calculates them.  Rejected
input retains its existing diagnostics-only contract, avoiding partial derived
facts.
