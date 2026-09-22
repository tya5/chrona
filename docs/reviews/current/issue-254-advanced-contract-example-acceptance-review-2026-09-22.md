# Issue 254 Advanced-Contract Example Acceptance Review

**Design authority:**
`docs/reviews/current/issue-254-advanced-contract-example-design-2026-09-22.md`
and its published corrections and implementation amendments.

## Accepted result

`main` commit `7ac9010782c3e086d8dd4c63d59287353306b39c` adds the sixth
HALCYON materialized slide, `flight-readiness`, and preserves all five prior
HALCYON SVG bytes. The artifact exercises the released Project v0.5 and View
v0.8 contracts without adding a schema, compatibility path, renderer target,
or geometry policy.

## Requirement evidence

| Requirement | Evidence |
| --- | --- |
| hierarchy, WBS, and planned-progress Project facts | `mission-closeout` rollup and its ordered FRR/Launch/LEOP/First-light children are validated Project input; the SVG exposes WBS cells. |
| Scenario comparison and provenance | `tvac-slip` is the automatic baseline; public materializer evidence records its id/title/content identity. |
| scheduler-owned float and criticality | Float cells show the selected chain's `+0d`; all 12 primary/scenario track combinations for the three selected relations use the `dependency-critical` marker. |
| Project link → selected title primitive | Only the FRR title cell is wrapped with the typed URL and accessible link title. The combined primary track is now correctly treated as primary provenance. |
| Theme responsibility | The existing `briefing` Theme explicitly maps the already-registered `dependency-critical` role; neither View nor renderer supplies a fallback. |
| existing public evidence | SHA-256 remains unchanged for `01` through `05`; `06-flight-readiness.svg` is the only added artifact. The programme-board's now-explicit ID selection preserves its earlier automatic-selection result while excluding the new rollup. |

## Verification

Focused local gates passed:

* `tests/integration/test_materialize_example.py`: 8 passed;
* generated-output, closure-input, and v0.5 review-content tests: 57 passed,
  7 skipped.

PR #268 passed the complete CI workflow on Ubuntu and macOS for both push and
pull-request runs. Each run executed conformance, reachability and import
direction checks, the full `pytest` suite, wheel build/reinstall, and an
out-of-checkout wheel smoke test.

## Architecture review

The implemented path remains unidirectional:

```text
Project facts -> Scheduler analysis -> View normalization -> Layout placements
-> Scene primitive metadata -> generic SVG serialization
```

The rollup, WBS, progress, link, and Scenario remain Project-owned facts;
criticality/float remain Scheduler output; View chooses the hierarchy,
comparison, visibility and table sources; Layout owns measured allocation and
routing; Scene attaches selected link metadata; SVG serializes it. No layer
re-parses upstream resources or derives geometry outside Layout.
