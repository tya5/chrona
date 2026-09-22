# Issue 120 — Draft Render Path Design Plan

## Objective

Replace the legacy one-file `chrona render` picture with an explicitly draft,
in-memory path that accepts authored resource paths and invokes the same review
render use case as immutable `render-review`.

## Questions to resolve

1. Define a draft closure construction boundary that validates all supplied
   resources without assigning snapshot identities or pretending to produce
   reproducible evidence.
2. Establish the CLI contract: required Project/View/Theme/Scheme/Layout;
   optional Actual, Summary, and Detail profiles; viewport, locale, output,
   and default packaged font metrics.
3. Decide the legacy command migration so two commands called `render` never
   produce incompatible visual models silently.
4. Confirm that draft construction feeds the existing closure → schedule →
   projection → content → measure → Layout → Scene → renderer pipeline.

## Architectural constraints

- The immutable Render Context path remains unchanged and is the only evidence
  and release path.
- Draft input assembly belongs above the use case; Layout, Scene, and renderer
  receive no raw paths or YAML.
- Schema validation and typed immutable contracts remain closure ingress work.
- Defaults must be declared and deterministic; no host locale or installed
  font discovery is permitted.

## Deliverables

Publish an English design review, an implementation plan, then one independent
implementation PR with CLI/use-case tests, compatibility review, full suite,
and public materializer regression checks.
