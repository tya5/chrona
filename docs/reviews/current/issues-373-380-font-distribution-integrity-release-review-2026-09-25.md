# Release Review: Font Distribution Integrity (#373, #380)

**Decision:** Accept, subject to three-platform CI.

## Delivered boundaries

- The substitute family is data-owned; RenderReview, not Layout or Scene,
  projects raster/PDF `drawn: false` warnings.
- The primary wheel has a 5,000,000-byte CI gate and no unresolved CJK extra.
  Plain primary development skips only provider-dependent evidence; CI installs
  the provider explicitly.
- The provider build records Source Han Sans 2.004R provenance, copies Adobe's
  matching notice, and writes Noto Sans JP Regular/Bold name records while
  preserving weights and source copyright/license records.
- The deterministic Context synchronizer updates the provider font closure;
  the public materializer verifies the regenerated Japanese corpus closure.

## Evidence

Focused provider/CJK/materializer tests passed. A plain primary editable
environment passed `725` tests with `25` stated optional-provider skips. The
provider-installed release gate passed conformance, documented commands,
structural checks, inventories, primary wheel size (`2,374,356 < 5,000,000`),
installed-wheel public smoke, and `pytest -n 4 -q` (`733 passed, 17 skipped`).
No unrelated generated SVG changed.

The final remote gate is Ubuntu, macOS, and Windows conformance for this
reviewed main commit, including wheel build/install and checkout-external smoke.
