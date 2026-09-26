# Architecture Review — Draft Host Cap Height (#447)

**Decision:** approve the [cap-height correction](../../design/issue-447-host-cap-height-correction-2026-09-26.md) before repair of H1's Ubuntu release gate.

| Boundary | Finding |
| --- | --- |
| Draft / immutable closure | Derived `H` bounds are permitted only for volatile Draft host faces; declared metrics retain the stricter import contract. |
| Face identity | Unicode cmap and outline come from the exact fontconfig-selected file and TTC index; no fallback face or synthetic weight is introduced. |
| Layout / Scene / adapters | The metric is closed before Layout. No downstream text measurement or paint repair is added. |
| Public evidence | Valid declared resources and their bytes remain unchanged. Ubuntu real-host 400/700, missing-cap-height and missing-`H` tests, all three-OS CI and public materializers gate acceptance. |

No unresolved architecture conflict. A host face without measurable uppercase
`H` is still explicitly unsupported, rather than rendered with an invented
cap height.
