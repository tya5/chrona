# M27 I27-R3A v0.5 SVG Role Adapter Review — 2026-09-21

**Decision:** Complete and published as the first R3 sub-slice.

The adapter serializes only completed SceneSurface primitives and resolves each fill
or stroke through `ThemeTokenView`; it has no raw Theme, View, Layout, Project, or
legacy paint-map access. The examples now bind all current core roles and their
immutable Context references were regenerated. Optional family composition remains
R3B and is not claimed by this review.

**Evidence:** `test_v05_svg.py`, full regression (195 passed), and conformance.
