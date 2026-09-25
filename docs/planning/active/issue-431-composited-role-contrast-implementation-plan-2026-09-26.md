# Implementation Plan — Composited Role Contrast and Corpus Visibility (#431)

**Design:** `issue-431-composited-role-contrast-design-2026-09-26.md`.
**Architecture review:**
`issue-431-composited-role-contrast-architecture-review-2026-09-26.md`.

## I431-1 — Shared composition extraction

Extract flat sRGB linearization, alpha composition, and contrast calculation
from `scene.perceptibility` into one pure Scene paint-analysis module.  Make
the existing policy-free `I_SCENE_PAINT_CONTRAST` observation call it without
changing its serialized findings.

**Files:** `scene/perceptibility.py`, new `scene/paint_analysis.py`, focused
Scene perceptibility tests.

**Acceptance:** existing observation fixtures retain their exact findings;
new direct kernel tests cover opaque and translucent flat paint; the module has
no Layout, renderer, raster, or font imports.

## I431-2 — Atomic role contract and corpus migration

In one publishable implementation unit, add finite semantic contrast classes,
state-text `contrastTreatment` and completed-Scene `contrastTreatment`
transport, decoration `backgroundTreatment: none`, typed
resolved-Theme access, explicit Scene `decorationDispositions`, and the
Theme-closure diagnostic `E_SCHEME_STATE_TEXT_CONTRAST`.  Migrate every
affected light/dark Theme declaration, regenerate every affected Scene/SVG,
and update schema/diagnostic inventories together.  Do not publish an
enforcing contract before every committed materializer context is valid.

**Files:** active Theme and Scene schemas/contracts, semantic registry,
`color_scheme.py`, `theme_tokens.py`, Layout decoration composition, Scene
model/serialization/validation, examples and generated evidence, inventories,
and focused schema/closure/Layout/Scene tests.

**Acceptance:** invalid state-text paint is rejected with its role path; each
classified state-text Scene primitive carries its resolved finite treatment;
`none` yields inspectable Scene absence without a drawable primitive; enabled
classified flat decorations are represented as completed paint; every
committed materializer context remains materializable; all five decoration
families have a visible corpus witness.  The View decoration selection must
express row and group policies independently; do not add a witness-specific
Layout branch.

## I431-3 — Checked policy report and release gate

Add the completed-Scene contrast policy evaluator and the deterministic
`tools/presentation_contrast.py` report/check command.  Reuse I431-1's kernel
and I431-2's registry/Scene facts.  Add the conformance entry once and commit
the generated per-purpose report with the I431-2 generated evidence; no
numeric baseline or suppression is permitted.

**Files:** new Scene contrast-policy and reporting modules, new tool and its
focused tests, `conformance/run_conformance.py`, generated report, release
review.

**Acceptance:** every below-floor classified decoration or state-text primitive
yields a stable error using only completed Scene facts; a malformed state-text
treatment yields a stable evidence-integrity error;
every declared absence is reported separately; report ordering is stable;
`--check` detects stale content; report includes all five decoration purposes
and state-text purposes; public materializer evidence and SVG diff are
intentional.

## Verification and publication

Run focused tests for each unit and `git diff --check`.  Before the final
release, run the contrast tool in check mode, generated-document/inventory
checks, public materializer reproduction, and a generated SVG diff.  The
three-OS CI full pytest/conformance/wheel matrix plus Python 3.12 public
materializer job is the full-suite release proof; do not duplicate full pytest
locally.  Fetch and compare `origin/main` immediately before each serial push.
