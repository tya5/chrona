# M25 Reachable Color-Path Inventory — 2026-09-21

**Decision:** Replacement design complete; implementation remains pending.

| Path | Current authority | M25 replacement |
|---|---|---|
| `scene/paint.py:legacy_theme_colors` | Theme role lookup plus seven literal fallbacks | Delete function; resolve the concrete Theme once from Theme + Scheme. |
| `scene/paint.py:resolve_facet_paint` | `facetPaints` / `paints` source-order lookup | Replace with Scheme category index plus resolved semantic intents. |
| `renderers/generic.py` | module literal colors and `_LEGACY_MUTED` | Delete legacy renderer route; it may accept only resolved Scene paint. |
| `renderers/scene_svg.py` | `groupPaints` fallback to group-band/text | Receive category colors already resolved in Scene; absence diagnoses. |
| `renderers/table_timeline.py` | Theme value lookup | Consume concrete resolved Theme values only; missing binding diagnoses before renderer entry. |

The implementation must delete, rather than wrap, each listed fallback. Tests must prove
that an absent Scheme reference and an absent color binding fail with a stable diagnostic,
and no renderer constant supplies paint. This closes the remediation condition in the M25
design review.
