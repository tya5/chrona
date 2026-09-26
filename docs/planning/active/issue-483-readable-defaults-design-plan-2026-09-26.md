# Design Plan — Readable Defaults (#483)

**Public base:** `bf98f9b0` on `main`. **Source of truth:** [Issue #483](https://github.com/tya5/chrona/issues/483), Specification 07 (Theme roles and tokens), Specification 34 (Color Scheme authoring), Specification 24, and the tuned catalogue presets from #470 (PR #485), which show the target look in YAML.

## Published baseline

Reproduced on `bf98f9b0` with the bare `chrona render` default (`chrona-default-draft`, which uses the HALCYON `briefing` Theme and the `mission-light` scheme) and with the copied `print-mono` preset:

1. **Axis boundary.** All 10 corpus Themes bind `axis-band-decoration.fill: surfaceRaised`, the same token as the group and row bands, at the group-band opacity. The axis band blends into the plot. The five bundle Themes already use `neutral`.
2. **Row guides.** The default draft has no row stripes in the plot, and member labels use `side: auto`, which places several names above their bars, on the boundary with the row above. Fixing this needs stripes across the plot together with group bands, which is #481's first defect (they exclude each other today).
3. **Source terminal.** Nine of the 10 corpus Themes bind `relationSourceTerminal` to the same filled triangle as the target end (`arrow` or `dependency-marker`). Only Controller Z `executive-light` uses a circle. `onboarding-variation` inherits from ASTER `executive-light`.
4. **`print-mono` colour.** `examples/halcyon-1/schemes/print-mono.yaml` paints `negative` in `#B00020` and `warning` (the as-of line) in `#7A5A00`. In greyscale, the slips, the as-of line and the muted text are all mid-grey, and the as-of line is a solid stroke like the gridlines. The scheme is shared by the `print-mono` preset and two corpus slides (`03-launch-campaign`, `09-gallery-mono`).

## Literal acceptance ledger

1. “The default draft and the shipped Themes draw a visible boundary between the axis and the plot: a rule, a band colour distinct from group bands, or both. A mechanical check compares the axis band's paint with the group bands'.”
2. “The default draft gives every bar a row guide across the plot, a stripe or a rule, and a name at its end in its own row.”
3. “`relationSourceTerminal` defaults to a circle or no mark in every shipped Theme. Committed evidence is regenerated.”
4. “`print-mono` renders slips and as-of distinguishably in greyscale.”

## Decisions to close

- Item 1: a band colour or a new axis rule. The YAML vocabulary already expresses a distinct band colour, as the presets do. A rule would need a new Layout primitive.
- Item 1: what the mechanical check compares (completed Scene paint, composited against the canvas) and where it runs (committed Scenes and the default draft).
- Item 3: the terminal size, relative to each Theme's target marker.
- Item 4: an achromatic `print-mono` palette with luminance-separated slip, on-track and ahead states, plus a dashed as-of line (the existing `dash` role property). This touches #423's dash vocabulary for one scheme only; #423 owns the general as-of rule.
- Item 2 depends on #481's combined stripes and bands. It is sequenced after #481 as its own slice.

## Slices

1. **I483-1:** items 1, 3 and 4. Theme and Scheme YAML across the shipped Themes; mechanical tests; regenerate all public evidence.
2. **I483-2:** item 2. Default-draft View and Layout, after #481 lands.
3. **I483-3:** literal acceptance review.
