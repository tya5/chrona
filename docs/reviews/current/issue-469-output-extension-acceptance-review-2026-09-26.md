<!-- chrona:literal-acceptance/v1 -->

# Release Review — CLI Output Extension and Target Identity (#469)

**Design plan:** [plan](../../planning/active/issue-469-output-extension-design-plan-2026-09-26.md).
**Design and architecture:** [design](../../design/issue-469-output-extension-design-2026-09-26.md),
[review](issue-469-output-extension-architecture-review-2026-09-26.md),
and [Specification 08 §3.2.1](../../specification/08-scene-and-rendering.md).
**Implementation plan:** [atomic slice](../../planning/active/issue-469-output-extension-implementation-plan-2026-09-26.md).

## Literal issue acceptance

### Issue #469

- Source: [Issue #469](https://github.com/tya5/chrona/issues/469)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `--output x.png` without `--format` writes a PNG, or fails with a diagnostic naming the mismatch; it never writes SVG bytes to a `.png` path. | met | [CLI test](../../../tests/cli/test_cli.py) renders the bundled Draft to `.png` and checks PNG magic bytes. A separate real CLI run produced a 1600 × 1122 RGBA PNG with `89 50 4e 47 0d 0a 1a 0a` header. | — |
| 2 | `--format svg --output x.png` is diagnosed. | met | [CLI test](../../../tests/cli/test_cli.py) checks exit 2, `E_RENDER_OUTPUT_FORMAT_MISMATCH`, `/output`, both targets in the message, and no file. The real CLI returned the same JSON diagnostic and left no `mismatch.png`. | — |
| 3 | A CLI test covers each known extension. | met | [Parameterized CLI test](../../../tests/cli/test_cli.py) parses the real `render` command and checks `.svg`, `.png`, `.pdf`, `.typ`, `.tex`, including case-insensitive spelling and explicit agreement. Additional tests cover unknown/extensionless names and guided/immutable parity. | — |

## Programme-level criteria (optional)

No additional programme criteria apply. All three literal issue criteria are
met without narrowing or deferral.

## Verification and artifact review

- Design plan `7cf7c7ccbfc3bb1b3a015a8562f8dc63802b3474` and design/review/specification `5e749f3fab58b9e0f747a35dfa234264e5ca1d36` were published before the implementation plan `6095f3dc3bd64cb9dc2cb068f53cda9a5fa45df2`; all three publication commits had green three-OS CI and newest-Python public materializers.
- Implementation `87b901319ab0de4eb55544b0f7b556935671f267`: focused CLI suite **69 passed**; diagnostic inventory and documented-command checks passed; full local conformance passed; all 21 public materializers reproduced byte-identically. The generated diagnostic inventory changed only for two new CLI diagnostic sites and line-number shifts; no public Scene/SVG generated artifact changed.
- Actual post-change output was checked with `file` and `xxd`: `board.png` is a 1600 × 1122 PNG, not SVG. A real explicit mismatch returned `E_RENDER_OUTPUT_FORMAT_MISMATCH` and created no output. [Implementation CI](https://github.com/tya5/chrona/actions/runs/36223044669) passed on three OSes plus newest-Python public materializers.

## Architecture conclusion

The output path is interpreted only at CLI ingress. Draft closure receives a single selected target; immutable Context remains target authority. Typesetter descriptor validation follows target selection, while Layout, Scene and adapters remain unchanged. The known-extension and unknown-suffix migration is explicit in the design and Specification 08. No renderer byte or public resource schema changed. All literal criteria are met; issue closure awaits this review commit's CI gate.
