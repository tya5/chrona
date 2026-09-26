# 43. Typography-aware source measurement

Each Layout source that renders text declares its semantic typography role. The Source Adapter resolves that role from the resolved Theme and measures inline extent, block extent, and first/last baseline with that role's font size and line height. Layout places the source with the same role and completes its baseline from the measured first baseline; Scene projects that completed text without measuring or choosing a coordinate.

At minimum, title uses `heading`; table text uses `text`; axis labels use `axis`; legend uses `legend`; notes and annotations use `annotation`. A missing or invalid role token fails through the resolved Theme token diagnostics; it never falls back to body text metrics.

A required slot whose assigned rectangle is smaller than this typography-aware
minimum retains its measured natural geometry. Layout records the placement
and required/available extents as a visible-overflow warning and completes the
canvas under Specification 33 Section 13. The historical `overflow: diagnose`
spelling does not turn a valid fit shortage into an error.

This policy changes no resource closure, no legacy Settings/Theme contract, and no renderer-specific geometry. The measured baseline is an immutable Layout input consumed by the Scene builder.

For an explicit draft system-font render, `numericSpacing: tabular` is a
request. If the exact selected face lacks tabular advances but has complete
proportional advances, draft closure resolves that role to proportional
spacing and emits `W_FONT_TABULAR_UNAVAILABLE` with role and face identity.
Layout measures and Scene/adapter paint the same effective mode. Missing
proportional digits, missing faces, and immutable metrics-contract violations
remain errors. The declared Theme is not rewritten and immutable public
contexts do not use this degradation path (#463).
