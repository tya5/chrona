# M25 Color Scheme Design Plan — 2026-09-21

**Status:** C25-D1/C25-D2 complete; C25-D3 remediation is required before implementation authorization.  
**Origin:** GitHub issue #27.  
**Milestone:** M25 — Color Scheme authoring.

## 1. Outcome

Chrona will let a user select a coherent named color alternative for a presentation
without editing individual Theme color tokens. The same Project, View, Style, Layout,
font/metric inputs, and output target must retain the same semantic selection and
geometry. A scheme changes only resolved color values.

## 2. Fixed authority boundary

| Layer | Retained authority | M25 addition |
|---|---|---|
| Style | semantic fact-to-role resolution | None |
| Theme | typography, spacing, marker/pattern, opacity, and role-to-color-intent bindings | Refers to scheme intents; does not contain an ordered palette policy |
| Color Scheme | None before M25 | Concrete semantic colors, categorical sequence, variants, and declared accessibility metadata |
| Render Context | immutable input closure | Binds one immutable Theme and one immutable Color Scheme |
| Scene / renderer | resolved primitives / serialization | Consume resolved colors only; do not select a scheme or supply defaults |

Project, Actual, View, Layout, and Scene identities remain unchanged by scheme choice.

## 3. Design gates

### C25-D1 — Research and use-case closure

- Compare Vega/Vega-Lite, ColorBrewer, and accessible palette practices as research
  inputs; record licensing/provenance of every built-in candidate.
- Close user tasks: semantic Plan/Actual/variance colors; deterministic team/category
  colors; light/dark alternatives; print/high-contrast suitability; same-document
  comparison gallery.
- Classify each color as semantic, categorical, surface/text, or out of scope.

**Exit:** each proposed field has a user task, a non-color cue requirement where needed,
and a provenance decision for built-ins.

### C25-D2 — Resource, resolution, and accessibility design

- Define a standalone versioned Color Scheme resource, immutable references, Theme
  bindings to a closed semantic-intent vocabulary, and deterministic category indexing.
- Define variant selection, inheritance/override limits, canonical identity, diagnostics,
  contrast/accessibility validation, and an explicit literal-color escape hatch.
- Specify Context closure and the resolution order: Theme + Scheme → concrete Theme →
  measured sources / Layout Manifest → Scene.
- Define gallery/preview as repeated deterministic Context evaluations, never as a
  renderer-specific override.

**Exit:** normative specification, ADR, schemas, positive/negative fixtures, and a
resolution matrix agree; no field allows semantic selection, layout, or renderer policy.

### C25-D3 — Replacement and whole-design review

- Audit Theme/Color Scheme/Style/Layout/Scene/Output boundaries and prove no second
  palette default exists.
- Decide the compatibility strategy for existing literal-color Themes; because no
  external compatibility promise exists, retain only the cleanest single authoring path.
- Review accessibility, deterministic assignment under group reorder, print/dark
  variants, source metadata, and AI/human common validation.
- Produce an implementation plan sliced into resolver, Context/CLI, examples/gallery,
  and final acceptance; publish it before code.

**Exit:** a design review explicitly authorizes implementation and records no unresolved
product decision.

## 4. Non-goals

- A generic design-token system, arbitrary expressions, renderer-local palettes, or
  automatic color inference from image content.
- Color as the sole semantic signal.
- Changes to Project facts, Style matching, Layout geometry, font metrics, or output
  fidelity claims.

## 5. Stop conditions

Stop before implementation and amend this plan plus the owning specification if research
shows that a requested built-in palette lacks redistributable provenance, a proposed
semantic intent cannot preserve its non-color cue, or a scheme choice would change
measurement/geometry or require a renderer fallback.
