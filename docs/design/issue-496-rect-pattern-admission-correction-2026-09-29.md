# #496 Rect pattern admission correction

**Status:** Accepted before Slice 2 implementation. **Authority:** Specification 07 pattern admission; follows the [selected design](issue-496-theme-asset-catalogues-design-2026-09-28.md).

The former catalogue-pattern allowlist included roles that can emit Symbol primitives, while the selected completed pattern geometry and adapter clip contract cover Rect only. Theme v0.13 therefore admits catalogue patterns only on the ten always-Rect role/property pairs in Specification 07. Existing non-catalog pattern tokens and Theme v0.11/v0.12 behavior do not change. Symbol patterns (including point marks, milestone swatches, and balloon callout/arrow boxes) need their own Layout-completed clip/paint contract; no silent Rect substitution or per-shape runtime branch is added. The #496 issue's literal criteria remain achievable with Rect-role patterns and catalogue glyph point marks.
