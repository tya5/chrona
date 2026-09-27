# Design — Readable Defaults (#483, with #423)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-483-readable-defaults-design-plan-2026-09-26.md). **Authorities:** Specifications 07 and 34; Theme v0.11 (`dash`, `marker`, `opacity`); the tuned presets from #470. **Also closes:** [#423](https://github.com/tya5/chrona/issues/423) (the dash vocabulary is used by nothing, and the as-of line differs from gridlines only by colour), whose change is the same Theme line as item 4.

No mechanism is added. Every item is expressible in current Theme and Scheme YAML, as the presets demonstrate. The work is to make the shipped defaults use it and to add checks that keep them readable.

## Item 1: axis boundary (band colour)

In each of the 10 corpus Themes:
- `colorBindings.axis-band-decoration.fill: neutral` (was `surfaceRaised`);
- a new `opacity.axis-band: 1` token bound to `roles.axis-band-decoration.opacity` (was the group-band opacity).

The five bundle Themes already do this. A rule would need a new Layout primitive and is not needed to meet the criterion.

**Mechanical check.** A new integration test reads the completed Scene paint:
- of every committed public Scene;
- of the default draft;
- of each bundled preset rendering HALCYON-1.

For each Scene, it composites the axis-band fill and every group-band and row-band fill over the canvas. It then requires a WCAG contrast ratio of at least 1.15 between the axis band and each band. Equal paint gives 1.0; the tuned presets reach at least 1.3.

Axis text on the darker band remains covered by the existing `presentation-contrast` conformance gate.

## Item 3: source terminal

Every corpus Theme whose `relationSourceTerminal` binds the target triangle gets its own circle marker token:
- `relation-source-terminal: {shape: circle, headLength: 5, headWidth: 5, attachmentOffset: 0}`, the preset value;
- `roles.relationSourceTerminal.marker: relation-source-terminal`.

Controller Z `executive-light` already uses a circle and is unchanged. `onboarding-variation` inherits it from ASTER `executive-light`; only its `extends` identity pin is refreshed.

A unit test resolves every shipped Theme, including the bundle Themes and inheritance, and asserts that the source terminal is a circle or none.

## Item 4 and #423: `print-mono` in greyscale, dashed as-of

**Scheme.** `examples/halcyon-1/schemes/print-mono.yaml` becomes achromatic:
- `negative: #000000`, so slips are the darkest state;
- `warning: #444444`;
- the other entries are already grey.

The variance states then separate by luminance:
- behind: `#000000`, relative luminance 0;
- on track: `textMuted #555555`;
- ahead: `positive #8C8C8C`.

**Theme.** Every shipped Theme's `as-of` and `asOf` roles take `dash: dash.as-of` with a `dashPattern` token `[4, 3]`. The as-of line then differs from the solid gridlines by line type, in every scheme. This is #423's convention: the current-date line reads as a dashed rule.

**Test.** Render HALCYON-1 with the `print-mono` preset and require:
- that the three variance states' completed fills differ pairwise by at least 0.1 in relative luminance;
- that the as-of stroke carries a dash while every axis-grid stroke has none.

## Migration

- YAML only: 10 corpus Themes, one Scheme, five bundle Themes (as-of dash only), and the `onboarding-variation` pin.
- **All public evidence changes, deliberately:**
  - darker axis bands;
  - circle source terminals;
  - dashed as-of lines;
  - the `print-mono` palette in `03-launch-campaign` and `09-gallery-mono`.
- The regenerated batch must show only these paint and marker changes. Any geometry change is a defect, apart from the terminal-marker geometry at relation sources.

## Out of scope

Item 2 (default-draft row guides and end labels) is slice I483-2, after #481. #478's role/property admission (the other session) must accept `dash` on `as-of`/`asOf`; this is a Path role that already serializes `dash`.
