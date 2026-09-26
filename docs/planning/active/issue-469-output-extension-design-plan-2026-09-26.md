# Design Plan — CLI Output Extension and Target Identity (#469)

**Issue:** [#469](https://github.com/tya5/chrona/issues/469).
**Public baseline:** `f21c34cdcc44cff856e14f5f91d4093a0fcb669f`
(`main`); #468's corrected review [CI](https://github.com/tya5/chrona/actions/runs/36222306349)
passed and #468 was closed before this plan was published.

## Published facts and limits

- The published CLI gives `render` and `render-workspace` a parser default of
  `svg` for `--format`, then writes target bytes to `--output` without looking
  at the filename extension. Both paths therefore can put SVG bytes in a
  `.png` file. The immutable `render-review` route has a Context target and
  an optional `--format` assertion, but also writes to a free output path.
- `resolve_draft_render` and `resolve_guided_draft_render` take an explicit
  target kind and enforce typesetter descriptor requirements. The target is
  decided before Scene/adapter production. Existing output-capability rules
  in Specification 08 and ADR-0018 keep adapters derived and target-specific.
- The issue report's reproduction at `aacedb9a` is historical evidence. A
  fresh CLI reproduction on this baseline wrote `<svg xmlns="` bytes into
  `.png` for both omitted `--format` and explicit `--format svg`; `file`
  recognized each as SVG, with no error. No change to renderer bytes or public
  materializer inputs is authorized by this issue.

## Literal issue acceptance

1. `--output x.png` without `--format` writes a PNG, or fails with a diagnostic naming the mismatch; it never writes SVG bytes to a `.png` path.
2. `--format svg --output x.png` is diagnosed.
3. A CLI test covers each known extension.

## Use cases and design questions

The primary user provides only a filename; the CLI must select the intended
target or reject before it writes. An explicit target and a filename must not
contradict each other. The same rule should be evaluated for guided Draft and
immutable Context output so the commands do not expose competing target
semantics. Typeset targets require a descriptor after target resolution.

Resolve these questions in the design, before product code:

1. Exact extension registry: `.svg`, `.png`, `.pdf`, `.typ`, `.tex`, and
   whether published examples' `.typst` spelling is a deliberate alias.
2. Extensionless and unknown-extension paths: which are allowed, and what
   target is inferred when `--format` is omitted? Should a supplied known
   suffix be case-insensitive? Avoid silently placing mismatched bytes.
3. Precedence and diagnostics for explicit mismatch, immutable Context
   mismatch, unsupported visual profile, and missing typesetter descriptor.
4. The ingress owner of path-to-target negotiation. Keep it in the CLI
   application boundary, before closure construction, with no adapter-side
   filename inference or Scene/geometry impact.
5. Migration effect of changing the Draft `--format` parser default from
   `svg` to absent. Update help/guides without introducing a second target
   registry in documentation or tests.

## Responsibility and architecture review

Review the selected rule against Specification 08, the target capability and
release contracts in Specification 22 and ADR-0018, Draft closure identity,
immutable Context target authority, output publication/overwrite behavior,
CLI JSON diagnostics, and the diagnostic inventory. Confirm that filename
metadata selects or validates an already-declared target but never changes a
completed Scene or causes an adapter to reinterpret output. Record any
intended incompatibility in the living specification or an ADR.

## Design slices and evidence

1. Publish this design plan with the issue's literal criteria and open
   decisions. Confirm the fresh baseline, both Draft paths, and immutable
   path behavior without overwriting user files.
2. Publish the resolved design, normative specification/ADR amendment if the
   public CLI contract changes, and whole-architecture review. Specify exact
   extension table, diagnostic code/shape, validation order, and migration.
3. Publish an implementation plan that separates target negotiation, CLI
   integration/help, tests and release review into independently verifiable
   units, each with files, focused tests, conformance, generated evidence and
   publication boundary. Only then edit product code.

Acceptance evidence must include a real `x.png` magic-byte check; explicit
SVG/PNG mismatch with no output file; tests for all known extensions and both
Draft entry points; immutable Context non-regression; focused tests,
conformance, public materializer byte check, full CI matrix, and a literal-row
acceptance review before issue closure.
