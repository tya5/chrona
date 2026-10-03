# Issue #911: packaged presets paint the named-period band as a light filled tint (work record)

Living record for [#911](https://github.com/tya5/chrona/issues/911) (C depth: preset and example YAML and resources only; from #880 item 1; board [#454](https://github.com/tya5/chrona/issues/454) is read only). Edited in place; Git keeps history. The owner-level choices are also recorded as a comment on #911 (options, choice, why, how to reverse).

**Public base:** `528377f4` on `main`. **Status:** record and implementation in one PR, record commit first. No core change was needed (if one is, stop and report).

## 1. Baseline

#911 has a body and no comment. #880 shipped the band as a 2 px outline in the scheme's `accent` (`text` in the print Themes) because (a) a translucent tint failed the contrast gate for marks lying on it (`E_SCENE_CONTRAST_GROUND_UNSUPPORTED`), (b) a new `period` scheme category breaks `--preset X --scheme Y` (`E_SCHEME_INTENT_UNKNOWN`), (c) a catalogue pattern needs the catalogue in every preset. What changed since: #995 (decoration findings warn; marks and text block), #1013 (a mark or label on a translucent host is judged on the host composited over the grounds beneath it), #980 (free labels are ground text). Verified on `main`: a Theme `fill` band with `opacity < 1` bound to an existing intent passes every blocking gate; the rest of this record is what to ship.

## 2. Literal acceptance (from the issue's proposal and the assignment)

1. Each packaged Theme paints the band with a fill that passes the contrast gate with marks on it.
2. No scheme category is required (`--preset X --scheme Y` works for every packaged scheme).
3. A synthetic test renders a period under every packaged Theme (`tests/integration/test_period_presets.py`), and sweeps preset by scheme.
4. The band reads as a light highlight, not a hole; labels on it meet the floor (#980/#1013); the perceptibility gate passes; before/after images read.

## 3. Decision (owner level)

| Option | Result |
| --- | --- |
| A. Translucent flat tint of an existing intent (`accent`, or `text` in `print-mono` and `technical-print`), role `period-band` with `backgroundTreatment: fill`, `period-band.fill` bound, opacity token 0.12 to 0.16 | Chosen. Binds only the closed intent set, so a scheme override re-colours it; no catalogue, no scheme category, no core change. |
| B. Catalogue pattern (`period-band.pattern`) | Not chosen: needs `iconCatalogs` in every preset and the default preset, and an opaque substrate that no intent supplies. |
| C. Opaque tint from a new scheme category or fall-back colour | Not chosen: Theme-language and scheme-schema change (core), the break #880 found. |
| D. Keep the outline | Not chosen: reads as a bracket, not a highlight. |

Opacity: light Themes 0.14, `print-mono` 0.12, dark Themes (`control-room-dark`, the HALCYON wallboard family) 0.16. 0.22 on the wallboard failed `note-index` text (4.07 against 4.5) on the composited tint; 0.16 gives 4.60. The band's own decoration contrast is 1.26 to 1.34 against a floor of 1.10. Reverse: set `backgroundTreatment: outline`, restore `strokeWidth` and `period-band.stroke` in the Theme (the #880 form).

## 4. Implementation (one slice)

- The eight packaged `theme.yaml` files: role, opacity token (drops the unused `period-stroke-width`), binding.
- The HALCYON example Themes that paint the period (`wallboard`, `wallboard-text-compression`, `wallboard-vertical-group-tags`, `editorial`, `editorial-readable-default`) the same way, and the two identity pins of `12-glyph-gates` (derived from `wallboard`). `target-b` (reviewer) and the annotation wallboard variants (#848) are untouched. Generated evidence is bot-regenerated, not edited.
- `tests/integration/test_period_presets.py`: fill-tint assertions, marks judged on the band ground, and a Theme x scheme sweep (56 pairs). 18 of the 56 pairs are refused by the scheme's own gates (scale mapping, inside-label and state-text contrast) for the plain View too; the sweep asserts the period adds no refusal. Those pre-existing Theme/scheme incompatibilities are not this issue's.
- Specification 50 (period-band paragraph) states the new packaged form.

## 5. Evidence

Rendered images read before and after: HALCYON 02 (wallboard), `executive-light`, `control-room-dark`, `print-mono`, `technical-print`, `editorial`. Corpus contrast report: 0 errors; warnings 79 to 80 (an `annotation-note-box` fill finding on `11-overlay-briefing`, a decoration warning only, in annotation artwork owned by #848). Perceptibility: PASS, 0 errors.
