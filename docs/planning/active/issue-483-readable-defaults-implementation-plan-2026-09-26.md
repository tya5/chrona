# Implementation Plan — Readable Defaults (#483, with #423)

**Authority:** [design](../../design/issue-483-readable-defaults-design-2026-09-26.md), [architecture review](../../reviews/current/issue-483-readable-defaults-architecture-review-2026-09-26.md).

## I483-1: axis band, source terminal, `print-mono`, as-of dash

**Files:**
- `examples/*/themes/*.yaml` (10), `examples/halcyon-1/schemes/print-mono.yaml`, `src/chrona/resources/presets/bundles/*/theme.yaml` (as-of dash);
- new `tests/integration/test_readable_defaults.py` (axis-band comparison, source terminal, greyscale variance and as-of dash).

**Evidence:** regenerate all 21 materializers; classify every Scene change as axis-band paint, relation source-terminal geometry, as-of dash, or `print-mono` palette. Refresh the contrast and coverage reports (`dashPattern` realized). View PNGs of one light, one dark and one mono slide.

**Gate:** focused tests, conformance, public `--check`, four-job CI. A separate slice review, which also carries #423's literal acceptance.

## I483-2: default-draft row guides and end labels

After #481 lands:
- `examples/halcyon-1/views/default-draft.yaml`: row stripes and member labels at `side: end` with fallback `[end, start, suppress]`;
- the default layout's `backgroundExtents`.

Test: every bar in the default draft has a row stripe across the plot, and every placed member label lies within its own row.

## I483-3: literal acceptance review, then close #483
