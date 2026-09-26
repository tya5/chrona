# Architecture review — suppression identity closure (#458)

**Correction:** [identity closure](../../design/issue-458-suppression-identity-closure-correction-2026-09-26.md).

Accepted. The mapping follows the IDs already produced by Layout and projected
by Scene. The gate observes serialized evidence without re-running Layout,
searching geometry, or changing adapters. It extends the #446 observer, and
does not add a second suppression policy. Validate with neutral fixtures for
each family and the complete committed Scene corpus.
