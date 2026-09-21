# 43. Typography-aware source measurement

Each Layout source that renders text declares its semantic typography role. The Source Adapter resolves that role from the resolved Theme and measures inline extent, block extent, and first/last baseline with that role's font size and line height. Scene composition MUST draw the source with the same role and place its baseline at slot block-start plus the measured first baseline.

At minimum, title uses `heading`; table text uses `text`; axis labels use `axis`; legend uses `legend`; notes and annotations use `annotation`. A missing or invalid role token fails through the resolved Theme token diagnostics; it never falls back to body text metrics.

A required slot with `overflow: diagnose` is rejected with `E_LAYOUT_REQUIRED_OVERFLOW` whenever its assigned rectangle is smaller than this typography-aware minimum measurement. This check occurs in Layout before Scene composition.

This policy changes no resource closure, no legacy Settings/Theme contract, and no renderer-specific geometry. The measured baseline is an immutable Layout input consumed by the Scene builder.
