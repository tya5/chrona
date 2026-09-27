# Architecture Review — Colour Scale Separability (#421)

**Decision:** design approved for implementation planning. **Reviewed design:** [#421 design](../../design/issue-421-colour-scale-separability-design-2026-09-26.md).

| Boundary | Authority | Result |
| --- | --- | --- |
| Scheme | Specification 34 suitability | Suitability claims become checked facts; no schema change. |
| Theme / View | Specification 60 | No syntax change; `resolve_color_scale` keeps its rejection rules and adds non-fatal collisions. |
| Layout / Scene / adapters | Specification 08 | Untouched, apart from Scene diagnostic strings. |
| CLI | #449 warning transport | One JSON warning per collision after the artifact is written, like the fit warnings. |
| #479 (future) | its generated palette | Will call the same check. |

**Risks:**
- CVD simulation is an approximation. The method and severity are stated, so the result is reproducible.
- Changing two Scheme categories changes public group-band and bar colours on the slides that use those schemes. This is intended; the batch diff must show only those colours.
