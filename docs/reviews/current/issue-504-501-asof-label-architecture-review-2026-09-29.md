# Architecture review — bounded as-of label placement (#501 R4)

Reviews the [R4 design correction](../../design/issue-504-501-asof-label-design-correction-2026-09-29.md) against the #501 acceptance text and Specs 07, 08, 38, 39 and 50, plus the #504/#501 selected design and current Layout/Scene boundary.

## Decision

The correction resolves a real contract conflict. #501 requires the label outside axis lanes and permits plot-top placement or a chip on the rule; the current generic overflow fallback may place it above the plot without fit validation, and can therefore cover axis text. Spec 50's adjacent seam fallback also admits axis-side placement. Both are superseded for the as-of label by finite, plot-side, obstacle-aware Layout placement and a typed suppressed outcome when no legal candidate exists.

The ownership map remains coherent: View/Actual supplies the as-of fact and label content; Theme supplies typography/chip metrics; Layout measures and completes the candidate, validates against the plot bounds and axis/data obstacles, and records the outcome; Scene emits completed rule and only a successfully placed label; SVG/PNG serialize. Layout adds the accepted label footprint before later annotation routing, so their order cannot erase this guarantee. No data meaning, View grammar, Theme tokens, Scene schema, or adapter policy changes. Specs 08 and 39 already prohibit Scene geometry decisions and define text/chip semantics; Spec 38's row membership and lane rules are unaffected. Spec 50 is the normative owner of generic surface feasibility and must carry this explicit as-of exception.

The outcome is deliberately conditional: the label is visible only if a legal plot-side candidate exists. On exhaustion the rule stays visible and Layout reports suppression; no axis overlap, mark overlap, clipping, or adapter repair is accepted. Ordinary label visible-overflow behavior remains unchanged.

## Review questions and evidence

- Candidate enumeration is finite, deterministic, and bounded to the plot-side region; no interpretation of “above” may cross into axis geometry.
- The obstacle inventory includes all axis bands and axis text plus all data marks and accepted required text. The rule-host exemption is limited to the intended label/rule attachment.
- Suppressed Layout text is non-drawable under Spec 08; test Layout evidence and Scene/SVG so a diagnostic cannot coexist with an emitted `as-of-label` primitive.
- The first-run gate covers the initialized starter and bare HALCYON, including the current `W_LAYOUT_LABEL_OVERFLOW` reproduction and a no-legal-space fixture.

No unresolved architecture issue blocks implementation. Exact visual spacing within the finite plot-side region is an implementation choice constrained by the stated order and bounds, not a new public option.

Follows the [design correction](../../design/issue-504-501-asof-label-design-correction-2026-09-29.md); the [implementation amendment](../../planning/active/issue-504-501-asof-label-implementation-amendment-2026-09-29.md) carries the slice gates.
