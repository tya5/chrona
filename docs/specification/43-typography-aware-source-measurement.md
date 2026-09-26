# 43. Typography-aware source measurement

Each Layout source that renders text declares its semantic typography role. The Source Adapter resolves that role from the resolved Theme and measures inline extent, block extent, and first/last baseline with that role's font size and line height. Scene composition MUST draw the source with the same role and place its baseline at slot block-start plus the measured first baseline.

At minimum, title uses `heading`; table text uses `text`; axis labels use `axis`; legend uses `legend`; notes and annotations use `annotation`. A missing or invalid role token fails through the resolved Theme token diagnostics; it never falls back to body text metrics.

A required slot whose assigned rectangle is smaller than this typography-aware
minimum retains its measured natural geometry. Layout records the placement
and required/available extents as a visible-overflow warning and completes the
canvas under Specification 33 Section 13. The historical `overflow: diagnose`
spelling does not turn a valid fit shortage into an error.

This policy changes no resource closure, no legacy Settings/Theme contract, and no renderer-specific geometry. The measured baseline is an immutable Layout input consumed by the Scene builder.
