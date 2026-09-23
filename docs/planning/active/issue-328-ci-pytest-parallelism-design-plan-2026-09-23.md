# Design Plan: Deterministic Parallel Pytest CI (#328)

## Verified starting point

The conformance workflow runs the complete pytest suite serially on both
`ubuntu-latest` and `macos-latest`. The same workflow also runs conformance,
structural gates, wheel construction, and an installed-wheel smoke test.
Parallelization must accelerate only test execution; it must not weaken either
platform, structural check, or package verification.

## Design questions

1. Establish serial and `pytest-xdist` result equivalence on the full suite,
   including skipped tests and generated-artifact checks.
2. Select a bounded worker count that is appropriate for hosted runners and
   does not oversubscribe macOS workers.
3. Define test isolation requirements: each test must own temp output and must
   not mutate committed generated evidence, environment-wide state, or shared
   snapshot roots.
4. Add a workflow concurrency group that cancels obsolete runs for the same
   branch/PR without cancelling the current commit's required checks.
5. Keep a reproducible local command and a documented rollback path.

## Architectural constraints

CI orchestration must not become a source of product policy. Test order may
vary, but output identity, diagnostics, materializer evidence, and public CLI
behavior must remain invariant. The project must not hide a race using retries
or split a full-suite requirement into incomplete shards.

## Required design and implementation outputs

1. A design review recording timing/equivalence evidence and worker selection.
2. A narrow workflow change that installs the explicit dev dependency and runs
   the whole suite with the selected worker count.
3. A concurrency policy scoped to workflow/ref.
4. Focused workflow-shape checks, serial-vs-parallel full-suite evidence, and
   one post-change public materializer verification.

## Publication sequence

Publish this plan; publish the design review; publish an implementation plan;
then make and verify the workflow change. If parallel execution exposes shared
state, stop and structurally isolate the responsible test/resource boundary
before enabling xdist.
