# M27 Axis Policy Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R2 is authorized under this rule.

I27-R2 preflight found no current authoring resource that declares an axis locale,
formatting preset, or fixed calendar level. Adding one would expand the public
resource surface, while choosing a renderer default would violate the closed-input
rule. The v0.5 runtime therefore owns one versioned, generic derivation rule:

1. construct candidate ISO calendar intervals with existing `layout.axis` for
   `year`, `quarter`, `month`, `week`, then `day`;
2. retain the most detailed candidate whose measured labels fit its own interval
   without overlap, using frozen `MeasuredSources` metrics and FontMetrics; and
3. if no candidate fits, diagnose `E_PRESENTATION_AXIS_OVERFLOW` before creating a
   Scene.

Labels are the existing locale-independent `AxisInterval.label` values. This is not a
hidden renderer default: it is a documented, deterministic Scene rule whose version
is carried by the v0.5 runtime. It has no Project/View/profile/example branch and
does not create a new persistent resource.
