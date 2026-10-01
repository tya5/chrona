<!-- chrona:literal-acceptance/v1 -->

# Issue #769 — evidence references acceptance review

Source: [Issue #769](https://github.com/tya5/chrona/issues/769), observed 2026-10-01 (one comment, the owner's decision "option 2"; body unchanged since 2026-10-01). Found by #731. Code and docs: [PR #771](https://github.com/tya5/chrona/pull/771) merged as [`09d63555`](https://github.com/tya5/chrona/commit/09d6355557a53ff05cfea01ceec7a1105dfbc9a3) ([PR CI](https://github.com/tya5/chrona/actions/runs/36847161758)). The owner's decision made a separate design pack unnecessary; the decision is the design.

## Literal issue acceptance

### Issue #769

- Source: [Issue #769](https://github.com/tya5/chrona/issues/769)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The spec and the code agree on whether an evidence reference is opened, covered by a test that fails if they diverge. | met | The owner decided to keep evidence references as shape-only records: reword Spec 17 and any guide text, add the test, and change no schema or version. The code was read first: [`profiles.py::_validate_value`](../../../src/chrona/extensions/profiles.py) is the only handler of an evidence reference in `src`; it validates a `resourceReference` field value (`artifacts`, `acceptanceEvidence`) against `revision-store-resource-ref-v0.1` and checks that its kind is allowed for the field, and nothing resolves the address, reads the target or compares `contentIdentity` (the function has no reader or store parameter and makes no read, open or resolve call; `resolve_package_manifests` reads only the package manifest in `extensions[].resource`). `IDP-EVIDENCE-001` is raised only for a value that violates the resource-reference shape, and `IDP-EVIDENCE-002` for a kind that does not match the field. [Spec 17](../../specification/17-implementation-delivery-profile.md) section 8 is now titled "Artifact and acceptance evidence references", states that they are shape-only records that chrona validates for shape and kind and does not open, resolve or verify, says `IDP-EVIDENCE-001` diagnoses a reference that violates the shape, notes that the conformance fixture's `verification` flags are declared harness inputs, and gives the revisit condition (open and verify only when a feature consumes evidence, then through the shared Store address guard with `contentIdentity` verification). The old text ("diagnoses failed immutable verification", "the owning Store verifies") was not true of the code, so no real check was deleted. The [test](../../../tests/unit/tools/test_evidence_reference_spec.py) reads files as UTF-8 through `pathlib` and has three checks: an AST scan of `src` finds every function holding a marker string for evidence references, and the set must equal the union of two registries the test owns (`SHAPE_ONLY_FUNCTIONS` holds `_validate_value`, `OPENING_FUNCTIONS` is empty), so a new handler fails until it is registered; each shape-only function must make no `read`, `open`, `resolve`, `verify` or `load` call and take no reader or store parameter; and while no opening function is registered, section 8 must say the target is not opened, resolved or verified and must not carry the old affirmative phrases. Restoring the old Spec 17 text makes the test fail naming all six old phrases. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Documentation and one consistency test; no code, schema or version change. The spec now says what the code does, and a feature that starts consuming evidence has to update the spec and the test together before it can merge.

Disclosures:

- **The detection is a heuristic by marker strings.** The AST scan finds handlers by marker strings (`resourceReference`, `acceptanceEvidence`, the two evidence kinds, `IDP-EVIDENCE-`); a consumer that reads evidence without any of those strings in the same function would not be seen. It guards the likely way a consuming feature would arrive, not every way.
- **No mutation check on the code side.** The only mutation run was restoring the old spec text; the code-side checks (a registered shape-only function that gains a read) were not mutated.
- **The conformance fixture still expects the old verdicts.** `conformance/implementation-delivery-evidence-v0.1.yaml` expects `IDP-EVIDENCE-001` for `immutable: false` and `contentMatches: false`. Those verdicts come from flags the fixture declares for the harness, not from chrona code, and the spec now says so; the fixture was not edited. If it should match the shape-only decision it needs a separate edit.
- **Nothing derived changes.** `docs/diagnostics/inventory.md` does not reference `IDP-EVIDENCE`, so CI's derived-sync regenerates nothing for this change.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #769; record that run in the issue closing comment.
