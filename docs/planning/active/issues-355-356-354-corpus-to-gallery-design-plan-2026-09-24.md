# Issues #355 + #356 → #354 — Corpus-to-Gallery Design Plan

**Status:** Proposed

## Purpose and dependency decision

The reusable design gallery is documentary evidence over a reproducible corpus;
it is not a renderer, a resource resolver, or a second authoring path.  PR
#356 supplies the semantic-register corpus substrate, but does not yet supply
the measurement/publication obligation of #355.  Therefore the delivery order
is deliberately:

```text
merge and release-review #356
        -> complete #355 coverage policy and published measurement
        -> design and deliver the feasible #354 gallery collection
```

No gallery set is permitted to use a semantic distinction that is not closed
by one project, Actual set, Snapshot, or Extension reference.  Conversely, a
coverage table is a curation backlog, never a render, schema, or CI gate.

## Published facts at planning time

- PR #356 (`examples/semantic-registers`, `b2fab02`) is clean against main and
  its Ubuntu/macOS conformance checks are successful.  It adds the fourth
  `orion-asic` corpus and semantic registers across Project, Actual, Snapshot,
  and Extension.
- Its own hand-over records the remaining #355 work: deterministic corpus
  coverage measurement and a published table.  It must not close #355 alone.
- #354's current gallery mechanism validates paired semantic provenance, but
  its current Controller Z set mixes two axes.  Its ten-set proposal has eight
  presently feasible sets; Japanese typography (#351) and multi-target
  evidence remain explicit blockers for sets 9 and 10.

## Architecture constraints

| Boundary | Owns | Must not do |
| --- | --- | --- |
| Corpus manifests and Contexts | Reproducible semantic and presentation evidence | Derive gallery policy at render time |
| Coverage tool | Read-only schema/corpus inventory and deterministic Markdown data | Fail CI merely for absent coverage |
| Gallery catalogue | Set membership, one declared Design Space dimension, narrative and provenance links | Select resources, alter a Context, or render output |
| Gallery generator | Read-only index/set pages, resource/reference diffs, inline declared SVG evidence | Become a second materializer or write corpus resources |
| Layout/Scene/adapters | Existing evaluation and output | Import gallery or coverage modules |

The catalogue's dimension vocabulary is closed to Specification 55:
`content`, `composition`, `visual-grammar`, and `appearance`.  A target matrix
is not a Design Space dimension; set 10 remains a separately documented future
target-evidence capability, rather than weakening the one-axis invariant.

## Phase 0 — Accept PR #356 as the corpus substrate

Before merge, fetch main, inspect the exact PR commit/range, confirm its two
GitHub conformance jobs and locally reproduce all declared manifests through
the public materializer.  Review generated SVG changes as one batch and check
that no legacy undeclared files are silently treated as evidence.  Merge only
if the PR remains fast-forward/clean; otherwise stop and rebase/review before
any #355 work.

**Acceptance:** main contains the four-register corpus, every declared slide
reproduces byte-identically, and #356 is closed.  #355 remains open.

## Phase 1 — Complete #355 corpus policy and measurement

Add `docs/guides/corpus-policy.md`, owned by corpus curation rather than the
gallery.  It defines one semantic register per project, extension-in-place,
and the rule that a new contract field needs an exhibiting project in the same
release unit.

Add a deterministic read-only `tools/corpus_coverage.py` that reads supported
schemas and declared corpus resources, produces a stable Markdown table of:

- schema field/vocabulary coverage by project/register;
- Project, Actual, Snapshot, and Extension contract coverage;
- exercised-by-no-project entries; and
- provenance links from each measurement row to source resource(s).

Publish the generated table in `docs/examples/corpus-coverage.md`.  Test its
determinism, declared-path handling, and representative missing/exercised
classifications.  Do not add a coverage threshold to CI; inventory validation
continues to validate declared evidence, not editorial completeness.

**Acceptance:** #355's five policy points are documented, measured, and
published; the report is deterministic and is explicitly non-gating.

## Phase 2 — #354 collection contract correction and generator design

Before adding more catalogue entries, publish a design correction that:

1. splits `controller-z-review-direction` into one Content set and one
   Visual-Grammar set;
2. adds required closed `comparison.dimension` and enforces one matching
   `comparison.axis`/dimension per set;
3. defines set-page inputs: catalogue entry, pinned Context provenance,
   declared materialized SVG, and a normalized resource-reference diff;
4. defines generated output locations and confirms they are disposable docs,
   never materializer evidence; and
5. consumes Phase 1's coverage report only as a displayed backlog.

The correction must specify stable diagnostics for mixed dimension, missing
peer, unequal semantic provenance, missing generated artifact, and malformed
reference diff.  Review it against Specifications 55 and 58 and the #348
decision that gallery packages/acquisition remain deferred.

**Acceptance:** a concrete, reviewed schema/tool plan exists before catalogue
or page generation code changes.

## Phase 3 — Implement gallery infrastructure and low-cost sets

Implement the contract/generator from Phase 2, migrate the existing catalogue
atomically, and create sets in the order below.  Each row is an independently
materializable, reviewable publication slice.

| Slice | Set(s) | New semantic/presentation authoring | Gate |
| --- | --- | --- | --- |
| G354-1 | 1 Executive status; split existing 3 Treatment ladder; 4 Two surfaces | catalogue/page provenance only | paired semantic identity and generated pages |
| G354-2 | 2 Four appearances | two Controller Z scheme-pinned Contexts | one Appearance dimension, materializer bytes |
| G354-3 | 5 Programme at scale | Context pairs over existing Halcyon resources; overlay only after #272 | one Composition dimension |
| G354-4 | 6 Investigating a slip | Context normalization over existing snapshot/scenario resources | one Content dimension |
| G354-5 | 8 Milestones, notes and margins | new View and Layout after their design review | one Composition dimension and four slot evidence |
| G354-6 | 7 What a bar can say | only after the remaining icon/encoding prerequisites | one Visual-Grammar dimension |

Every slice updates the coverage report/page and checks that its resource diff
contains only the intended presentation references.  A required new View or
Layout follows the normal design → review → implementation-plan workflow; it
is never smuggled in as a gallery fixture.

## Phase 4 — Deferred sets and collection release gate

Set 9 is blocked by #351's CJK measurement/font/target design.  Set 10 is
blocked by a future manifest evidence model for PDF/Typst/TikZ, and is not a
Specification-55 Design Space set.  The gallery index lists both as deferred
backlog with their blockers; it does not fabricate preview evidence.

At each G354 slice run focused tests.  At collection milestones batch the
expensive work once: full pytest, conformance/structural gates, every declared
public materializer, generated-SVG diff review, installed-wheel smoke, and
GitHub CI on both platforms.  Publish serially after checking remote main and
the exact commit range.  Close #354 only once all non-blocked planned sets are
published and deferred sets are explicitly represented with their blockers.

## Out of scope

Package acquisition, guided package consumption, semantic extension redesign,
unrelated legacy-artifact deletion, #351 implementation, and multi-target
manifest redesign are not implied by this plan.  Each needs its own approved
design before it can unblock a gallery set.
