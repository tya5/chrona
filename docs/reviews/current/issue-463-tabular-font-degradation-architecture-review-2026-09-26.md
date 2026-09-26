# Architecture Review — Missing Tabular Digits (#463)

Reviewed against Specifications 08 and 43, #410 metrics-v3, #447 host-face
capability, #449 visible degradation, ThemeTokenView, font closure, Layout
source measurement, Scene TextLayout and SVG/PNG adapters at `39426438`.

The selected rule changes only volatile draft host resolution. It must not
silently rewrite the source Theme or immutable closure; a per-render effective
treatment is appropriate. This keeps exact selected-face metrics and paint in
lockstep. A missing proportional mode is still a resource error; the warning
cannot be used to conceal it. Scene and CLI receive the same typed record.

Decision: design accepted for implementation planning. The implementation
must test both successful fallback and unchanged packaged corpus. Host-specific
Hiragino/Georgia evidence is required on macOS; portable fixture tests alone
do not establish the literal acceptance criterion.
