# Issue1826 — design self-checks

[Pre-code design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1826#issuecomment-6290560393).
Specs60 (`b12de2c7e`) and33/46/49 (`5a2fcaa8f`) were public before affected code.
One issue PR; no authored public-corpus adaptations or new schema, threshold,
tolerance, Scene geometry or adapter policy.

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| every pair of drawn legend swatches is checked with the existing Spec 60 measure, under normal vision and the scheme's declared colour-vision types. A synthetic case warns for the ΔE 2.7 pair and for identical swatches with different meanings. | focused checks met; release pending | `test_legend_diagnostics.py` exercises the completed-placement path for ordinary keys, the specified colours under normal/protanopia/deuteranopia/tritanopia, identical different-meaning inks, both source subjects, and hidden/text-only controls. Existing final-ink and typed ScaleCollision dedup remain. |
| a halo is excluded from the decoration contrast check by its declared purpose (it is a separator, not a figure). target-b can then drop decoration: none (reviewer YAML follows). | focused checks met; release pending | `test_contrast_policy.py` checks canonical separator, arbitrary identity, wrong/absent purpose and Text misuse, while retaining ordinary bands, marks, Text and graphical legend floors. `test_semantic_vocabulary_closure.py` checks the fresh host identity and rejects stale styled Scene identity. Reviewer owns the target-b YAML follow-through. |
| content-width legends measure with the same rounding they place with (no false ellipsis), the one-row height is the measured row height, and a synthetic test covers both. | focused checks met; release pending | `test_legend_measurement_closure.py` checks exact natural widths at three origins in block/inline/grid, genuine shortage, and shared wrap offsets. `test_legend_known_width_completion.py` checks real fixed-parent rendering, wrapping/shortage, tall swatches and Draft auto; fixed outer dimensions stay fixed. |

Ownership review: Layout compares completed legend ink and owns shared finite
measurement/placement arithmetic and known-width row completion. The host
vocabulary declares the separator's contrast disposition; Scene contrast uses
an exact graphical role/purpose join with conservative fallback for misuse.
Existing classified role/Text precedence remains. Fresh closures bind current
host bytes; no Context pin or stale-identity compatibility alias is added.
Independent Luna review caught and corrected the Text misuse edge before
publication. General optional-decoration synthetic coverage remains; a halo
is no longer falsely required as a decoration witness.

Focused own-venv batch:315 passed, one obsolete ordinary-pair expectation
corrected; directly affected37 tests then passed. Independent final registry,
contrast and report review:91 passed. Fixed/auto SVG and render-plan tests:
8 passed after the final internal naming cleanup. These batches overlap.
The separate pre-existing block-stack/tall-swatch measurement defect is tracked
as [#1830](https://github.com/tya5/chrona/issues/1830), not silently folded into
this inline-row acceptance.

Initial [CI39424696347](https://github.com/tya5/chrona/actions/runs/39424696347)
passed conformance, MCP and newest-Python reproduction; pytest had37 failures:
20 stale CLI warning expectations,7 overprint fixtures without canonical
purpose metadata,7 materializer fixture checks and3 fixed Scene digests.
Disposition is fixture migration, not a weaker product rule. The three old
digests are recovered exactly by substituting only the prior vocabulary SHA;
SVG digests stay unchanged. Ten test-only materializer Scene mirrors are
regenerated: only the host identity and15 finite-coordinate legend residues
change; all10 SVG mirrors, primitive IDs, labels, routes and diagnostics stay.
Seven affected fixture materializer checks pass. A broader local materializer
run also passed33 tests but found6 expected stale public-example checks because
this source-only worktree does not apply CI's disposable snapshot; those public
checks passed in the official snapshot. Public derived files remain unauthored.
Focused corrections:20 CLI cases,7 overprint cases,3 digest cases and7 affected
materializer cases pass. The18 golden stdout changes contain only the intended
new legend warning; status, artifacts, exit/stderr and existing warnings stay.

The [official initial artifact audit](https://github.com/tya5/chrona/pull/1831#issuecomment-6291305105)
contains every slide's primitive/text/route/diagnostic count and actual SVG
before/after visual review. Final test-only correction must reproduce the
same public artifact tree; do not repeat the expensive local corpus sweep.

PR1831 final head92c6134e2 and CI39428114449 passed; final artifact12266877360
reproduces every audited payload (SHA256d471b10b1d9fa5b459cb7114eabb4d435cac9bf1c7239e5a4290c20592e41cfe).
Exact-main c4ead79ed release39431151167 passed Ubuntu/macOS, MCP and newest
Python, but Windows had one failure (14,430 passed/73 skipped): the hash-seed
test child printed a Unicode diagnostic under cp1252. Windows conformance and
OS probe passed; dependent wheel steps were skipped, so release remains open.
The test-only correction explicitly sets the child PYTHONIOENCODING to UTF-8,
matching its existing parent decoder, without changing product diagnostics or
the three-seed equality check. Focused test passes under ambient cp1252.
This red-main correction lands with PR1834 to avoid a separate serial cycle.
Fresh exact-main three-OS release evidence remains required before closure.
