# Architecture review — elevated preset starter compatibility (#460)

**Design:** [#460 design](../../design/issue-460-elevated-preset-starter-design-2026-09-26.md).

Accepted. Specification 63 already admits per-effect decorative omission on
baseline and requires Scene, not the adapter, to apply it. #377 fixes target
selection outside the preset's four-resource bundle; adding a target property
to a preset would cross that boundary. The chosen flat fallback preserves
semantic group distinctions and existing rich-profile output. The library
matrix will be discovered from the shipped manifest so adding an entry cannot
evade the gate. Residual risk: a visually weak flat fallback must be checked
in the rendered starter SVG, not inferred from successful Scene construction.
