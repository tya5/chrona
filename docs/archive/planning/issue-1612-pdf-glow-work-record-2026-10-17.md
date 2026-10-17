# Issue #1612 — PDF completion work record

## Baseline and design authority

Ready base: `fa262ebab648229138eb34c33bf6a821f6450e96`. Font closure and measured-source face closure are published by PRs #1619 and #1621. PDF completion merged as PR #1635, commit `315b9b32b84b8769926a8b751bdef99b1d935f22`; its exact head `9f4640c9e783e5bcea5eb55ee4969b614cd842ca` passed [CI run 39004437658](https://github.com/tya5/chrona/actions/runs/39004437658). Issue #1612 is closed: final-review main `2ff197828dd1b8ef1f2573202d201129a6d00b9b` passed [three-OS release 39007088159](https://github.com/tya5/chrona/actions/runs/39007088159).

The pre-code PDF design was published in `a2918bf202b51e974813b02c6649af63f9fe1d8a`; the mixed-run correction is governed by the published Specs 08 §2.3 and 63 §7.1 correction (`a885135e8838197ff2008c092371a80d30102b25`, [review finding](https://github.com/tya5/chrona/issues/1612#issuecomment-6229304765)). Specs 08/63 are normative; Specs 30/33 retain Layout ownership of face choice, advances and geometry. The [architecture and implementation plan](https://github.com/tya5/chrona/issues/1612#issuecomment-6225435042) remains the whole-system review authority.

## Literal issue acceptance

| Literal issue acceptance | Disposition |
| --- | --- |
| Synthetic test: a Theme naming only a Latin family renders a CJK string through the fallback and records which face it used. | Met. |
| All 15 presets render a Japanese CSV import to PNG, SVG and PDF with no glyph error, on macOS and on the Linux CI runner (Noto CJK package). View three PNGs and one rasterised PDF. | Met. macOS rendered all 45 preset/target outputs; three PNGs and one rasterized PDF were viewed. Exact-head Linux pytest passed all three shards. |
| Public SVG/Scene byte-identical for Latin-only examples. | Met. The current [artifact 12090094644](https://github.com/tya5/chrona/actions/runs/39004437658/artifacts/12090094644) has 109 retained paths, 0 added/retired, all 50 SVGs and 50 Scenes byte-identical to ready base `fa262ebab648229138eb34c33bf6a821f6450e96`, and 0 primitive or Scene diagnostic changes across all 50 slides. Only `docs/diagnostics/inventory.md` (source locations/new constructors) and `declared-value-inventory.md` (the deliberately pinned PDF raster identity) differ. |
| Reviewer: please trace it and fix it in the face-run path, with a synthetic twin of a mixed Latin+CJK string checked for weight in PNG (and the same in PDF). | Met. [Mixed-script PNG/PDF controls](../../../tests/integration/test_mixed_script_raster_faces.py) verify the actual Latin crop against same-position regular/bold references in portable and native Hiragino cases; PDF text maps to embedded 400/700 programs. The native no-projection control fails as expected. |

## Approved architecture and implementation slices

The three approved slices are complete: (1) registered PDF profile/closure with pinned halo engine evidence; (2) PDF-only glow raster lowering plus exact closed-font aliases and isolated Form resources; (3) shared completed-run positioning used by private PNG input and PDF halo clones. Layout remains the only owner of measurement and face selection. Scene carries completed geometry/paint. Adapters only serialize it; none discover fonts or measure text.

| Slice | Owned files and verification |
| --- | --- |
| Profile/closure | `visual_capabilities.py`, `closure.py`, CLI choices and shared vocabulary/Context schemas; admission, closure, schema-equivalence and packaging controls. |
| PDF serialization | `pdf_glow.py`, `pdf_fonts.py`, `pdf_opacity.py`, registry; native assets/collection index/permissions, clips, transforms, RGBA/soft masks, source text, isolated nested opacity and no-glow controls. |
| Mixed-run projection | `svg_text_runs.py`, PNG registry and PDF halo lowering; multiline/scale/rotation/alias and conditional-identity controls, plus full task-table/member-label PNG/PDF twins. |
| Release | `test_automatic_cjk_fonts.py`, literal acceptance review and public artifact comparison; exact-main three-OS/conformance/wheel/reproduction gate before closure. |

The PDF peer admits baseline geometry, glow and native cap/join while optional omission remains supported for existing presets. Explicit baseline and unsupported-required refusals remain. Glow lowering uses completed filter regions and closed native font files, keeps vector source paint/selectable text, and preserves clipping and opacity through isolated resources. It fails closed on unsupported grammar or absent/mismatched engine evidence with existing typed diagnostics; adapter identity pins the glow/font/raster grammars and engine version. No whole-page rasterization, public SVG/Scene change, preset/example edit, new Scene field, or PDF permission rule for PNG is introduced.

The mixed-run correction positions each completed run from Layout's prefix advances, tracking and scale in private adapter copies. It preserves exact serialized/inherited PDF aliases, multiline offsets, rotation and whitespace; PDF source text is lowered once, separately from its halo clone. Latin-only PNG input and adapter identity remain unchanged. Native/portable task-table and member-label tests demonstrate weight-sensitive full PNG output and corresponding embedded PDF fonts.

## Final release evidence

Exact-head CI 39004437658 passed all three pytest shards (4,201 / 4,195 / 4,210), conformance, MCP, reproduction, derived preview and readiness. The current snapshot audit confirms 109 public paths retained with no SVG/Scene or primitive/diagnostic changes. The CJK integration module passed 48 tests on macOS, including all 45 outputs; current three PNGs and rasterized PDF were viewed. Marquee retains 74 glow images/soft masks, extractable Japanese text and vector source paint.

Focused evidence includes 34 projector/halo/registry/PDF-advance tests, 61 renderer/font/opacity controls and 48 CJK integration tests. The exact-head no-projection native control fails, confirming the mixed-run test detects the original defect. Final release 39007088159 passed Ubuntu (9,022 + 3,644 tests), Windows (12,664) and macOS (12,671), each with conformance, OS probe and installed-wheel smoke, plus MCP-floor and newest-Python reproduction of every public materializer. Archive preparation passed 13 focused documentation tests; its conformance gate is supplied by CI.
