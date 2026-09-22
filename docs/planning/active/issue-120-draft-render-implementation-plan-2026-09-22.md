# Issue 120 — Draft Render Implementation Plan

## I120-1: Draft closure factory

- Add a presentation-ingress factory accepting resource paths and declared
  defaults; load YAML, call `parse_contract`, resolve Theme/Scheme, and return
  `RenderClosure` plus the packaged font-metrics root.
- Synthesize only an in-memory context with `draft` identities.  No snapshot,
  context file, hash, or revision artifact is written.

## I120-2: Replace the CLI render adapter

- Replace legacy `render` arguments and generic renderer dispatch with required
  View/Theme/Scheme/Layout paths and optional Actual/Summary/Detail paths.
- Parse viewport and locale explicitly; use packaged metric defaults; pass the
  draft closure to the unchanged review use case.
- Make help text identify the command as draft/non-evidence.

## I120-3: Verification and publication

- Test factory schema errors, CLI syntax/defaults, optional profiles, and a
  public-example draft render equal to immutable review bytes.
- Run focused CLI/use-case/closure tests, full pytest, module checks, five
  public materializers and generated-SVG diff checks.
- Publish one implementation PR; after two-platform CI, merge and close #120.
