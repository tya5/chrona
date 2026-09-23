# #328 Deterministic Parallel Pytest CI: Acceptance Review

## Accepted change

The conformance workflow retains its Ubuntu/macOS matrix, conformance and
structural gates, wheel build, installed-wheel smoke test, and step order. Its
single full-suite invocation is now `pytest -n 4`; `pytest-xdist>=3.8.0` is an
explicit dev extra. Workflow concurrency cancels obsolete runs only for the
same workflow/ref or pull request.

## Verification

| Check | Result |
| --- | --- |
| Fresh editable install with `.[dev,render]` | xdist available |
| Serial full suite | 420 passed, 7 skipped, 88.10 s |
| Parallel full suite | 420 passed, 7 skipped, 29.22 s |
| Parallel focused public materializer/renderer set | 19 passed |
| Shared-state review | materializer corruption test isolated with an owned example copy |
| Generated evidence | public materializer artifacts remain verified by the suite |

## Architecture review

The only exposed race was a test mutating a repository fixture. It was fixed by
copy-on-write isolation, not by retrying or excluding it from parallel runs.
No product boundary or public rendering behavior changed. The fixed worker
count preserves predictable resource use across both hosted operating systems;
CI retains one complete suite rather than sharded partial gates.

## Disposition

#328 is complete and may close. Future test mutations must own copied fixtures
before modifying them.
