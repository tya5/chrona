# Architecture Review — Reproducible Example Evidence and Reachability (#441)

**Design reviewed:**
`issue-441-reproducible-example-evidence-design-2026-09-26.md`.
**Decision:** Accepted.

| Boundary | Review result |
| --- | --- |
| Manifest → materializer evidence | The manifest remains the only authority for public generated SVG/Scene files. The reachability tool observes its paths; it does not regenerate or alter them. |
| Context → local resources | Typed reference records own closure edges. The walker follows local paths only and leaves package assets to the existing closure resolver. |
| Repository → quality gate | Git-tracked example files are the measured population, avoiding untracked scratch files and making an orphan a deterministic error. |
| README → public artifact | Root README images gain a narrow contract: direct references to declared generated SVG evidence. Documentation elsewhere and historical archives are unaffected. |
| Schema test → corpus population | The test consumes reachability's declared View population. It validates current public sources rather than preserving broad filesystem migration work. |

## Whole-architecture conclusion

The change reinforces the existing source → Context → materializer → generated
evidence flow. It does not add a second renderer, a gallery asset cache, or a
documentation-owned output format. The reachability graph is deliberately
repository-level inspection, analogous to inventory/conformance checks, so it
cannot blur closure resolution into layout or adapter responsibilities.

Using the manifest-generated SVG directly is the cleanest README contract:
the exact path that reproduction checks owns is the path readers see. The
ASTER deletion is therefore an atomic removal of dead topology, not a silent
migration to another unowned preview.

No design correction is required before implementation.
