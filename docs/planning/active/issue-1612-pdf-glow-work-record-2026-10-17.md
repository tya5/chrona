# Issue #1612 — PDF completion work record

## Baseline and design plan

Ready base: `5cc04dd5b59079650f27da6434b80ad9d8be9f8b`.
The font and measured-run corrections are published in PRs1619/1621;
[release38985610444](https://github.com/tya5/chrona/actions/runs/38985610444) passed.
[Current acceptance](../../reviews/current/issue-1612-automatic-cjk-fonts-acceptance-review-2026-10-17.md)
is44/45 outputs: Marquee PDF refuses required glow, independently of language.
Complete that output, not a waiver or a flattened page. PR1623 lands first;
the PDF work has no overlapping product files.

| Literal issue acceptance | Current disposition |
| --- | --- |
| Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | Met by published font controls; retain them. |
| All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | Not met: Marquee PDF still refuses. Re-run all45 without the refusal exception. |
| Public SVG/Scene byte-identical for Latin-only examples. | Published font evidence met; repeat against the ready base after PR1623. |
| Reviewer: please trace it and fix it in the face-run path, with a synthetic twin of a mixed Latin+CJK string checked for weight in PNG (and the same in PDF). | Not met: [mixed-script PNG weight finding](https://github.com/tya5/chrona/issues/1612#issuecomment-6229304765); trace exact completed faces through the full PNG and PDF, including provider-absent Hiragino. No speculative font substitution. |

## Design and whole-architecture review

Normative authority: [Spec63 §7.1](../../specification/63-portable-visual-capabilities.md)
and [Spec08 §2.4](../../specification/08-scene-and-rendering.md), published before code
as `a2918bf202b51e974813b02c6649af63f9fe1d8a`.

- Closure pins the optional halo engine and exact font files; Layout retains
  measurement/geometry (Specs30/33). Scene retains completed paint/profile
  admission (Specs46/63). Only PDF syntax adaptation changes.
- The new registered PDF peer admits baseline geometry, glow and native cap/join.
  Optional omission remains allowed: elevated-light and Sunday depend on it.
  Explicit baseline and unsupported-required refusals remain exact. No preset IDs,
  new Scene Image field, font discovery or authoring-coordinate policy.
- Keep vector source/selectable text. Exact native-face aliases preserve assets
  sharing a family/weight. Temporary independent references prove matching glyph
  alpha and actual title/kicker halo RGBA; all74 Marquee halos retain soft masks.
- Each isolated PDF Form owns its resources. Unequal nested alpha exposes a v1
  resource omission; correct it in the opacity owner, not through glow conditions.
  PDF opacity identity becomes v2; incorrect nested output intentionally changes.
- Spec56: preserve frozen vocabulary v0.1; publish a versioned shared profile
  definition and update its consumers. Add optional `glowRasterizer` evidence in
  Render Context v0.17 without a top-level version bump. Reuse one descriptor
  definition, register/package parts, and record schema-equivalence deltas.
- Fail before artifact creation on unsupported paint, unresolved fonts or missing,
  unavailable or mismatched engine evidence using the existing stable diagnostics.
  Reject whole-page rasterization, name-only face selection and new optional-effect
  failures. No independent numeric performance or visual-error threshold is added.
- Mixed-run weight is an additional required correction, not waived by successful
  output generation. Compare actual full PNG glyphs with the measured regular/bold
  assets and the matching PDF. Keep Layout face choice/measurement authoritative;
  do not move fallback selection into adapters. If the trace exposes a missing
  contract, publish the selected correction before implementation. PNG raster use
  must not inherit PDF-only embedding-permission refusals.

## Implementation plan and publication

| Slice | Owners and evidence | Acceptance/publication boundary |
| --- | --- | --- |
| 1. Profile/closure | `visual_capabilities.py`, CLI choices, `closure.py`, vocabulary/Render Context schemas, inventory/registry; peer, omission, explicit baseline, unsupported-required and descriptor tests; schema equivalence. | One coherent commit after the published design; preserve all existing valid Contexts. |
| 2. PDF serialization | Private glow/font-alias lowering; `pdf_fonts.py`, `pdf_opacity.py`, renderer registry. Test exact assets/collection index/permissions, RGBA/soft masks, completed region/patterns, source text, clips/transforms, unequal nested opacity and native cap/join. | No global library patches or source-file mutation; keep the existing no-glow dependency path. |
| 2b. Mixed-run weight | Trace the reviewer strings through measured run assets/weights, SVG spans, actual full PNG and embedded PDF faces; provider and native OS cases. Choose the bounded owner correction only from that evidence and add a synthetic exact-face twin. | Complete design/whole-architecture review before code if a contract gap exists. This required finding keeps the issue open. |
| 3. Acceptance | Remove the Marquee refusal exception; run45 real outputs locally/CI, view three PNGs and a rasterized PDF, compare all public SVG/Scene bytes and inspect generated reports as a batch. | One PDF PR after1623, focused local tests; full three-OS/conformance/wheel/reproduction in CI. Close only after the literal review and its exact-main release pass. |

Update this record and the existing acceptance review in place. Publish the design,
implementation and final review as coherent commits; no additional per-slice plans.

## Current implementation evidence

Profile/closure admission controls: `pytest -q` for
`test_visual_capabilities.py`, `test_glow.py` and `test_draft_closure.py`:
76 passed. The PDF peer is selected only by the existing same-version preference
rule; an explicit baseline still refuses required glow. Draft pins halo evidence
inside the ReportLab descriptor; a vector-only PDF never verifies that engine.
Vocabulary/schema-parts/package controls:196 passed. Schema equivalence against
`origin/main` (L1):PASS, added1/delta3/equal35; four exact allowed delta paths,
zero stale entries pruned. Frozen vocabulary v0.1 is unchanged.
PDF serialization is implemented:37 focused glow/registry/native-face/opacity
tests and59 existing PDF controls pass. Completed aligned strokes and rotated
text retain their geometry; every admitted cap/join remains a native PDF operator.
The no-glow path does not verify resvg. Independent architecture audit found no
remaining blocker; it checked exact-face closure and isolated Form resources.

macOS: `pytest -q tests/integration/test_automatic_cjk_fonts.py` passes48tests,
including all45 real preset/target outputs without the Marquee refusal exception.
Root viewed default, executive and Marquee PNGs and the actual rasterized Marquee
PDF in `/tmp/chrona-1612-final-visual.aSJfqb`. Its Japanese text is extractable;
74completed glows produce74alpha images/soft masks, with source vectors retained.
Linux exact-head CI, post1623 public byte comparison and review-containing
three-OS release are still required; the issue is not accepted or closed.
