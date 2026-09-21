# Color Scheme Authoring Research — 2026-09-21

**Status:** C25-D1 input; non-normative.  
**Decision supported:** Color Scheme is a standalone resource that provides semantic
colors and a categorical sequence; it is not a general color-scale system.

## Sources

- [Vega Color Schemes](https://vega.github.io/vega/docs/schemes/) distinguishes named
  categorical schemes from sequential, diverging, and cyclical schemes, and permits
  explicit scheme registration.
- [ColorBrewer 2.0](https://colorbrewer2.org/) classifies qualitative, sequential, and
  diverging palettes and exposes colorblind-safe, print-friendly, and photocopy-safe
  selection criteria.
- [WCAG 2.2 §1.4.3](https://www.w3.org/TR/WCAG22/#contrast-minimum) requires 4.5:1
  contrast for normal text and 3:1 for large text at Level AA.

## Findings applied to Chrona

| Research finding | Chrona decision |
|---|---|
| A categorical palette is an ordered set for discrete domains. | `category` is an immutable ordered list; assignment uses a stable key and canonical hash, never View order or renderer state. |
| Sequential/diverging ramps encode quantitative values. | Out of M25: Plan/Actual/variance are named semantic states, not scalar color scales. A later scale feature needs its own specification. |
| Named schemes make comparison cheap. | Context binds one named Scheme; a gallery evaluates the same immutable Context once per named Scheme. |
| Palette suitability depends on medium and color vision. | Scheme metadata declares `colorVision`, `print`, and `background` suitability, but a declaration never removes Theme markers/patterns/text alternatives. |
| Text contrast is mechanically testable. | D2 must define contrast checks for every text/background pair, with WCAG AA as the baseline. Non-text state distinctions remain independently encoded. |

## Closed C25-D1 user tasks

| User task | Required result | Classification |
|---|---|---|
| Switch one review from light executive to a cool or warm direction. | Same facts, geometry, source metadata, and non-color cues; changed resolved color values only. | semantic/surface |
| Compare several coherent alternatives before deciding. | Deterministic gallery of one Context evaluated once per selected Scheme. | preview |
| Show teams/categories. | Stable category key always receives the same palette index for the same Scheme. | categorical |
| Identify plan, actual, behind, and unknown. | Fixed semantic intents with Theme-owned marker/pattern/label support. | semantic |
| Produce an accessible review. | Declared contrast evidence plus non-color differentiation; no claim that color alone is sufficient. | accessibility |

## Provenance decision

M25 will not copy external palette bytes merely because a palette has a familiar name.
Vega and ColorBrewer are research references. A built-in Scheme must declare its exact
source/provenance and license in its resource metadata, and D2 must reject a built-in
without that evidence. The initial D2 fixture set may use Chrona-authored values; an
external palette is admitted only after its exact redistribution terms are recorded.

## Exclusions

Arbitrary interpolation, host color-management inference, image-derived palettes, and
continuous visual encodings are excluded. They would either add a quantitative scale
authority or introduce renderer-dependent behavior outside the issue's user tasks.
