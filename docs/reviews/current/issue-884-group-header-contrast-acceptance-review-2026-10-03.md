<!-- chrona:literal-acceptance/v1 -->

# Issue #884 — group header text contrast class, acceptance review

Source: [Issue #884](https://github.com/tya5/chrona/issues/884), observed 2026-10-03 (body unchanged since filing, re-fetched before this review; the four comments are this session's claim, owner decisions D3 to D5, and state notes, no other contributor's). The issue has no checklist; its two literal requirements are copied below. Living record: [work record](../../planning/active/issue-950-884-contrast-ground-2026-10-02.md) (shared with #950); living contract [Specification 46](../../specification/46-completed-scene-paint.md) section 8 and [Specification 50](../../specification/50-constraint-driven-gantt-surface-quality.md) (group tint). Owner decisions (D3 how to classify, D4 the floor, D5 the pattern ink; options, choice, reversal) are [a comment on the issue](https://github.com/tya5/chrona/issues/884#issuecomment-5954366050).

Slices: design, architecture review and implementation plan, [PR #961](https://github.com/tya5/chrona/pull/961) (`c9e3b459`); code, [PR #964](https://github.com/tya5/chrona/pull/964) (`7ee197bc`). No schema, Scene, Theme or diagnostic-code change, so the S0 gate is not applicable; it passed in the PR.

## Literal issue acceptance

### Issue #884

- Source: [Issue #884](https://github.com/tya5/chrona/issues/884)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Give the role a text contrast class (as table cells have). | met | The registry class `ContrastClass.GROUND_TEXT` is assigned to `groupHeader` in [`semantic_registry.py`](../../../src/chrona/presentation/model/semantic_registry.py) and resolved by purpose (`contrast_binding_for`), because the header text keeps the shared role `text`; [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py) gates it at the required 4.5:1 floor on the completed band under it, with a catalogue pattern's substrate and ink as two grounds. Every committed render with a group header now reports it: corpus contrast report 0 errors, new `group-header` rows (83 primitives, 22 slides, minimum 11.94). 36 public slides byte-identical. | — |
| 2 | Add a synthetic test where a tint equals the header ink. | met | [`test_group_header_gate.py`](../../../tests/integration/test_group_header_gate.py) renders a Project grouped by owner through `control-room-dark` with a tint equal to the header ink: an `E_SCENE_STATE_TEXT_CONTRAST` error on that group's header only, ground colour the tint; a legible tint gives info only. Scene-document unit tests in [`test_group_header_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_group_header_contrast.py) cover flat, gradient and pattern grounds, the floor, v0.6, and that other text in the role `text` is not classified. Mutation checks: 13 of 13 killed. Rendered images read: the tinted header is invisible and the gate reports it; a legible tint renders. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The header text is judged on the surface it lies on, by the same Scene observer that already reads tints for marks and stripes; no Layout, Scene, Theme or adapter contract changed. The catalogue-pattern ink ground generalizes the canvas-texture rule to every pattern host for classified text and marks.

Disclosures:

- **Pattern reachability.** No Theme role admits a catalogue pattern on a group band today, so header-over-pattern is proved on Scene documents; the generalized ink ground is live for the period band, axis band and label chips. No corpus Scene has a pattern host, so the corpus report is unchanged by it.
- **Judgement calls D3 to D5** (purpose-keyed class, fixed `required` floor, general pattern ink) are recorded on the issue with reversals.
- **Remaining ungated text.** Other text in the role `text` that lies on a tinted band (table cells, group detail) is still not gated; that is outside this issue's text, no acceptance row depends on it, and the classification is one registry line if wanted later.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #884; record that run in the issue closing comment.
