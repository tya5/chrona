# Implementation Plan — Axis Lanes, Cells and Rule (#426, I426-2)

- **Code:**
  - `schemas/theme-v0.11.schema.yaml` (the three properties);
  - `model/theme_tokens.py` (readers);
  - `model/semantic_registry.py` (`axisRule`, `axisCellSeparator`);
  - `layout/surface_composer.py` (lane pre-pass, centring, inset, cell gap, separators, rule);
  - `scene/v05_builder.py` (Path projection).
- **Resources:** all 15 shipped Themes bind `axis-rule`; the 5 bundle Themes and Views adopt lanes, cells, separators and inset.
- **Tests:**
  - unit tests for lane centring, band-in-lane, gap, separators, inset, and the legacy byte path;
  - a preset render test;
  - the evidence batch, where the only change should be the added axis rule.
- **Follow-up issues:** corner shape, ticks, two-label cells.
- **Review:** a superseding acceptance review for all ten rows.
