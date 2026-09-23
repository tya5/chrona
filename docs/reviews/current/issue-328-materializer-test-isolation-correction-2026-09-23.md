# #328 Materializer Test Isolation Correction

## Trigger

The first focused `pytest -n 4` run exposed a deterministic race: the
materializer mismatch test temporarily modified the repository's committed
`examples/controller-z/generated/executive.svg`, while another worker was
materializing that same public evidence.

## Correction

The mismatch test now copies the complete Controller-Z example to its own
`tmp_path` before corrupting expected evidence. The test continues to prove
that a changed expected SVG is rejected, but no longer mutates a shared source
fixture. This is the required structural isolation; no retry, worker exclusion,
or serial-only exception is added.

## Review

Public generated artifacts remain immutable inputs to all tests. Every test
that intentionally mutates an example must first create an owned copy, as the
existing stale-pin and bad-font tests already do. With this correction the same
focused integration/renderer set passes under `-n 4` (19 passed).
