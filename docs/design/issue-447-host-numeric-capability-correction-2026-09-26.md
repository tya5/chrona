# Design Correction — Host-Font Numeric Capability (#447)

Real macOS `fc-match` and fontTools verification select `Hiragino Sans` 400
from face 0 of its TTC by English typographic family. Its measured default
digits are proportional and it has no usable tabular-digit feature. The
existing importer requires a valid tabular advance map for **every** font,
even when a draft Theme only requests proportional spacing; this rejects the
selected host face before Layout. This is a design gap, not a fontconfig
failure. Helvetica Neue and Verdana do pass the current numeric extractor.

Decision: exact numeric capabilities belong to each selected face. Immutable
declared-metrics-v3 descriptors retain their current complete proportional
and tabular contract. Volatile draft host metrics may contain a proper subset
of modes when the face cannot supply a mode. The extractor records only modes
whose actual glyph advances satisfy that mode's invariant. `FontMetrics.width`
continues to reject a selected mode absent from the face with
`E_FONT_METRICS_UNAVAILABLE`; it must never simulate tabular digits with
spacing or silently switch the Theme policy. Draft closure should validate
the modes actually requested by its typography roles before Layout; a
proportional-only Hiragino Theme can render, and a Hiragino role explicitly
requesting tabular diagnoses with role/family/weight context.

Architecture review: this keeps capability and exactness in font closure,
not Scene or rasterization. It does not weaken immutable font evidence or
change the v3 on-disk descriptor. Layout receives a metric whose available
features are already known; resvg paints the same selected face. The
correction extends the [combined design](issues-457-447-fit-and-host-font-design-2026-09-26.md)
and supersedes its implicit assumption that every selected host face yields
both numeric modes.
