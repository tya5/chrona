# Issue #54 strict example-closure design review

| Boundary | Decision |
| --- | --- |
| #44 resource format | Preserve opt-in pinning for general callers. |
| Canonical examples | Treat as strict reproducible evidence fixtures. |
| Materializer | Validate pin presence and byte identity before CLI invocation; never repair metadata. |
| Font assets | Apply the same strict-presence rule and emit the specific missing-identity diagnostic. |
| PR #53 | Pin-only update is compatible with this strict fixture profile; it adds no runtime fallback. |
| SVG evidence | Remains public-materializer output and must remain unchanged in check mode. |

The separation avoids turning #44 into a global breaking requirement while giving published
example evidence a complete immutable closure. No Settings/Theme compatibility path is
introduced. Design is complete; implementation may proceed.
