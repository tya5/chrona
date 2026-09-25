# Architecture Review — Visible Row-Density Policy (#400)

**Decision:** accepted for implementation planning.

## Boundary review

| Boundary | Decision | Result |
| --- | --- | --- |
| Layout Profile → Layout | v0.9 declares finite draft/immutable row-density policy. | Pass: generic text overflow is not overloaded. |
| P1 requirement → row placement | P1 remains the sole requirement authority; Layout selects normal, diagnose, or proportional compact outcome. | Pass: no duplicated track arithmetic. |
| Layout → Scene | Completed row clip hosts, references, and `RowDensityOutcome` cross the boundary. | Pass: Scene does not select policy or calculate compression. |
| Scene → adapter | Admitted adapters serialize completed clips; unsupported typeset adapters reject. | Pass: no adapter-local crop/fallback. |
| Draft/immutable ingress | Closure revision supplies explicit Layout mode; profile supplies both policies. | Pass: no renderer or undocumented use-case default. |

## Invariants accepted

1. Ordinary `E_LAYOUT_MARK_OVERFLOW` remains a hard invariant.  Only a
   selected compact outcome can deliberately attach completed mark/text clips.
2. Every source item retains a placement and identity under compaction; no
   item is removed as a surrogate for fitting.
3. Row clip host, clipped primitive, and row slot must share the completed
   row identity.  Scene validation must reject dangling, cross-row, or
   paint-visible-only clip references.
4. `W_LAYOUT_ROW_DENSITY` is structured Layout output, emitted to draft
   authoring stderr and serialized into inspection evidence.  It is not an
   adapter warning.
5. `rowDensityClip` must be present in a completed surface only when all
   selected adapters admit it; Typst/TikZ reject rather than omitting it.

## Migration review

Layout Profile v0.9 is the only live reader.  All profiles and Contexts must
migrate atomically, with current immutable profiles declaring `diagnose`.
The draft default is intentionally `compact-with-warning`; it is a disclosed
product-policy change, not a compatibility promise.  No source implementation
may begin until schema migration, outcome data model, and target capability
tests are planned as one release.
