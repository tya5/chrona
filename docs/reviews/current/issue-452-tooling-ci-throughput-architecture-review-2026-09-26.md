# Architecture Review — Tooling CI Throughput (#452)

**Decision:** accepted for implementation.

| Boundary | Accepted responsibility | Rejected responsibility |
| --- | --- | --- |
| `chrona.resources.safe_load` | Safe, canonical product YAML decoding | Tool report policy or cross-run cache state |
| Independent presentation coverage loader | Safe parsing without product imports | Importing a product loader, renderer, or SVG parser |
| Run-local loader cache | Reuse of equal path bytes during one report computation | Persisted cache, freshness inference, or error suppression |
| Reachability and realization report | One traversal/discovery followed by finite filtering | Skipping identifiers, families, or repeated-output characterization |
| CI | Full cross-platform validation | Treating a local benchmark as a correctness gate |

The design preserves the repository's dependency direction.  In particular,
presentation coverage's ability to run without `chrona.` imports is stronger
than reuse of the product helper.  The shared cache is deliberately scoped to
one top-level report call; it is an implementation detail below validation,
not a new resource authority.

The proposed source policy catches the exact regression class identified in
#452 while permitting explicit `yaml.load` only with a named safe loader.  It
does not prohibit legitimate test fixtures or third-party YAML boundaries.

No presentation, layout, scene, materializer, or renderer semantics change.
The acceptance suite must retain byte-identical reports and current malformed
input failures, then obtain full-suite evidence from CI.
