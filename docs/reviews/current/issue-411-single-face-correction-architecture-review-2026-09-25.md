# Architecture Review — Single-Face System-Font Scope (#411)

**Decision:** accepted.

The restriction follows an existing boundary rather than creating a new
one: `FontMetrics` has no implicit role/weight selection, so passing a
heterogeneous Theme would make an adapter paint a face Layout did not
measure.  Rejecting it at draft ingress keeps selection outside Scene and
adapters and makes the limitation visible.

A metric catalog belongs to the Theme-to-Layout measurement contract and
would affect declared as well as system faces.  Deferring that cohesive #410
extension is preferable to introducing a system-only parallel measurement
path.  The single-face resolution remains volatile and does not weaken the
immutable Context or materializer boundary.
