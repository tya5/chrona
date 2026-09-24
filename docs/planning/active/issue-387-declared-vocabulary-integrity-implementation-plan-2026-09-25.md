# Implementation Plan: Declared Vocabulary Integrity (#387)

**Status:** Proposed

**Implements:** [Declared Vocabulary Integrity design](../../design/issue-387-declared-vocabulary-integrity-design-2026-09-25.md)

## I387-1 — Generated vocabulary inventory and quality gate

Add the version-pinned declared-vocabulary registry, deterministic inventory
tool, generated documentation, `--check`, and focused negative tests.  The
tool compares only named finite contract paths to their owner acceptance
evidence and records explicit open-ended dispositions; it is not imported by
runtime code.

**Files:** `tools/vocabulary_inventory.py`, its policy/registry input,
`docs/diagnostics/` generated report, focused tool tests, and repository
quality entry points.

**Acceptance:** stale output, missing owner, unclassified field, unknown
schema path, and declaration-wider-than-accepted all fail deterministically;
the current five divergences appear as explicit failing/boundary work rather
than hidden exclusions.

**Publication:** focused tool tests and generated-output review in one commit.

## I387-2 — Owner contract migration

Move Theme to v0.6, View to v0.13, and Render Context to v0.15.  Constrain
marker/pattern names at Theme loading, close locale to deterministic `en-US`
and `ja-JP` formatting, and require the currently implemented object/facet/
endpoint annotation anchor form.  Migrate all shipped resources and every
schema registry/parser reference atomically; retain no legacy readers.

**Files:** Theme/View/Render Context schemas and parser registry, Theme token
normalization, compact date formatting, annotation validation boundary,
examples/conformance/test fixtures, Contexts, generated inventories, and
focused schema/model/Layout/render tests.

**Acceptance:** each five-case invalid document is rejected before adapter
serialization; `ja-JP` compact dates render deterministically; no shipped
closure names an obsolete contract; Theme/View/Context declarations agree with
their owner acceptance tests.

**Publication:** focused product and schema tests, migration diff review, and
public materializer regression in one implementation commit.

## I387-3 — Corpus and release gate

Regenerate only public artifacts affected by the Context/Theme/View contract
migration through declared materializers.  Add structure tests proving adapter
modules do not own Theme marker/pattern or locale acceptance, run full quality
checks, and publish an acceptance review.

**Files:** regenerated Context/resource/generated evidence where required,
structural tests, generated report, release review.

**Acceptance:** all public materializers reproduce byte-identically; generated
SVG diff is intentional and reviewed; focused and full pytest, conformance,
diagnostic/declaration/reachability checks, wheel smoke, and Ubuntu/macOS/
Windows CI pass.

**Publication:** generated evidence and release review are separate commits;
close #387 only after the GitHub CI evidence succeeds.
