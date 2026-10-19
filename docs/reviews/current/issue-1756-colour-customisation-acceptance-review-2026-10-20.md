# Issue 1756 — customisation acceptance

Status: dev A rows 1–2 implemented at `eca1ac1bf577a142e9f9cca48c00587b5fa7807c`;
PR/public-snapshot and exact-main release gates pending. Dev B owns rows 3–5.
Current design, architecture review and implementation plan:
[issue Status](https://github.com/tya5/chrona/issues/1756#issuecomment-6256669837).
Normative authority: Specs 28 and 60, including exact domain-warning coverage
correction `b9c9e0b41`, published before the affected implementation.

| # | Literal acceptance criterion | Status and evidence |
| ---: | --- | --- |
| 1 | An encoding whose realized slot colours are indistinct from each other, or from another legend key's colour, gets a warning naming both, using Spec 60's existing distinctness measure. Show it on a synthetic case. | Met locally; release pending. `test_legend_colour_warning_render.py` checks real View/semantic and same-scale/same-value distinct Style meanings, both warning subjects/names and their actual Scene/SVG ink. Near values within one scale retain the existing domain warning only when typed collision facts cover that exact pair. Layout unit tests cover declared vision simulations, hidden keys, completed multipart/stroke/transparent/gradient behavior and uncovered measurements. |
| 2 | Find whether this is intended; make both modes consistent or state the rule, and add a synthetic test. | Met locally; release pending. Spec 28 states the canonical point semantic rule. `test_gate_encoding_modes.py` proves ordinary Theme-gate points are outside View `target: planned`, forecast points are eligible, and omitting the optional Theme gate role makes both use the planned fallback. It checks real SVG and serialized Scene encoding; no project exception or unsupported Style gate encoding is added. |
| 3 | The guide shows the colour-by-field recipe working on at least two bundled presets, plus title and subtitle customisation, checked by the docs tests. | Deferred to dev B's [PR1765](https://github.com/tya5/chrona/pull/1765); not accepted by this A-only review. |
| 4 | The message names the role and what to declare, or the preset declares the role (reviewer YAML). | Deferred to dev B/reviewer; not accepted by this A-only review. |
| 5 | The error says that a parent path is not permitted and names the allowed form; the guide states it. | Deferred to dev B; not accepted by this A-only review. |

## Actual output and architecture

[View encoding versus semantic key](assets-1756/view-encoding-semantic.png):
`Team a` is `#269D78`, `On track` is `#269D79`; warning
`W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.291` names both. The test joins each
warning subject to its exact Scene swatch and SVG `data-scene-id`/fill.

[Distinct Style meanings on one scale/value](assets-1756/same-scale-same-value-style.png):
`Planned owner: a` and `Actual phase: a` both realize `#269D78` and produce
the paired legend warning. No distinct-domain-value collision exists for
the one-value scale, so sharing its name does not suppress the warning.
Other realized Actual-key collisions remain reported, not filtered from the test.

Presentation supplies explicit scale/domain identities and existing resolved
`ScaleCollision` facts. Layout reads only final visible completed legend ink,
uses existing CIEDE2000/vision measures, and suppresses only an exact existing
domain-pair finding. No ID/field parsing, secondary scale resolver, threshold
change, Scene placement/paint decision or adapter policy is introduced.
The intended visual delta is zero geometry/paint changes; new warning and
Scene diagnostic records are intentional. CI must verify public per-path counts.

## Verification and release

Combined focused batch: **184 passed** (colour scale/arithmetic, Theme tokens,
diagnostic messages, Style/View legend content, final handoff/diagnostics and
both real-render integration modules). Independent source/contract review
found no blocker; `git diff --check` is clean.

Local `conformance/run_conformance.py`: every check passes except
`diagnostic-inventory`, which reports `E_DIAGNOSTIC_INVENTORY_STALE` for source
line movements and the added typed Theme accessor error site. That report is
derived-owned (`tools/derived_report_inventory.py`); do not author its snapshot.
The CI-generated snapshot must pass inventory/conformance before acceptance.
Full pytest and newest-Python public materializers run in CI; do not duplicate
the full suite locally. Keep issue1756 open until all five literal rows and the
review-containing exact-main three-OS/conformance/wheel release are complete.
