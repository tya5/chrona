<!-- chrona:literal-acceptance/v1 -->

# Issue #980: free-label contrast, acceptance review

Source: [Issue #980](https://github.com/tya5/chrona/issues/980), re-fetched 2026-10-03 (body unchanged since filing; one owner comment widening the scope to other shared-`text` labels over tinted group bands; the later comments are this work's claim, [owner-level decisions](https://github.com/tya5/chrona/issues/980#issuecomment-5964401560) and a status block). The rows below are the literal asks of the body's Direction and of the owner comment; the body has no acceptance table. Work record: [issue-980-free-label-contrast-2026-10-03.md](../planning/active/issue-980-free-label-contrast-2026-10-03.md); living contracts [Specification 46](../../specification/46-completed-scene-paint.md) section 8 and [50](../../specification/50-constraint-driven-gantt-surface-quality.md).

Slices: design [PR #1005](https://github.com/tya5/chrona/pull/1005) (`b94847ed`); C980-1 (class, tests, specification, corpus fixes) and C980-2 (packaged presets) [PR #1010](https://github.com/tya5/chrona/pull/1010) (`eb95ec1c`; derived-sync bot commit `8c06d33f`).

## Literal issue acceptance

### Issue #980

- Source: [Issue #980](https://github.com/tya5/chrona/issues/980)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Add the purposes whose text can lie on a decoration ground (as-of label, member label, period label where unclassified) to the `ground-text` class one registry line at a time. | met | [`semantic_registry.py`](../../../src/chrona/presentation/model/semantic_registry.py): `as-of-label`, `member-label` (outside, and the four inside roles) and 25 more label bindings carry `ContrastClass.GROUND_TEXT`, one argument per registry line; the period label was already `STATE_TEXT`. `contrast_binding_for` resolves by purpose with the role `text`, or by role and purpose. [`test_free_label_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_free_label_contrast.py) (41 tests, hand-built Scenes: each label shape fails on a dark canvas and passes in a legible ink; a tinted band, opaque chip, region frame, pattern in both colours, canvas texture and the as-of cone, inside, straddling and outside, are the ground) and the registry guard in `test_semantic_registry_contrast.py` (every `label` binding classified). 17 of 17 mutation checks killed. | none |
| 2 | Run the corpus contrast report and fix any Theme that then fails in its YAML (never relax the 4.5 floor). | met | The floor is unchanged (4.5, `required`, blocking, no Theme knob). The report over every committed Scene has three new errors, all `examples/controller-z`, fixed by value choice in the slides' own Theme YAML: `axis-label2` white on the accent quarter band 3.67 to `insideLabelPlanned` (`axis-tiers`, `axis-cell-corners`), `note-index` 3.28 to `textMuted` (`annotations`); images read before and after. The generated report on the bot commit `8c06d33f` ([`presentation-contrast.md`](../../diagnostics/presentation-contrast.md)) has `Findings: 6603; errors: 0; warnings: 0`. `halcyon-1` and the reviewer's `21-target-b` have no finding (not edited). The same gate over the packaged presets found `executive-light`, `elevated-light` (`axis-label2` 3.67), `technical-print` (month labels on the halftone, 1.0; ink `neutral`, image read) and the note-index ink of three presets, fixed in YAML; [`test_preset_label_contrast.py`](../../../tests/integration/test_preset_label_contrast.py) sweeps all seven presets. | none |
| 3 | Axis labels. | met | [`semantic_registry.py`](../../../src/chrona/presentation/model/semantic_registry.py): `axis-label` in the shared role and the second and third tiers (`axis-label2`, `axis-label3`) are ground text; tests above cover the three; the two real corpus findings and the `technical-print` finding were axis labels. | none |
| 4 | Other text in the shared `text` role over tinted group bands is still not gated (owner comment). | met | [`test_free_label_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_free_label_contrast.py): table cells and column labels, group details, title and subtitle, legend, project notes, relation labels, milestone digest entries and summary text are ground text; a label over a group band is judged on the band (`test_a_tinted_band_under_the_label_is_the_ground`); the corpus report shows `table-cell` and the other purposes at the required floor with 0 errors. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

The registry says what a role is (one classification per label binding); the completed-Scene policy is unchanged and is still the only judge; Theme and preset YAML chose inks; Layout and adapters are untouched. No floor, class, code or ground rule changed; classifications only grew. No schema or Scene change.

Disclosures:

- **Wider than the three named purposes** (decision J1 on the issue): every Text purpose is classified, with a guard test so a new label purpose cannot reopen the hole.
- **A translucent label chip or panel cannot be judged** and is the blocking `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` (the existing rule for text on a translucent host); no committed Theme has one. Successor: [#1013](https://github.com/tya5/chrona/issues/1013) (searched translucent host, translucent chip, contrast ground: no duplicate).
- **The as-of label over a strong cone fails the gate** in the synthetic cone render test: the case the issue was filed for, now asserted.
- **One corpus datum outside the findings was edited:** `examples/halcyon-1/themes/editorial.yaml` mirrors the packaged `editorial` preset byte for byte (one line, required by `test_public_preset_evidence`).
- Packaged presets declare no annotation roles, so their `note-index` bindings are an inherited value, checked against the scheme grounds directly.

Exact review-bearing-main three-OS CI and the newest-Python materializer run must pass before closing #980; that run is recorded in the closing comment.
