# #322 Example Roles Acceptance Review

**Authority:** Specification 58 and the #322 design and implementation plan.

**Result:** Accepted.

The public corpus is now explicitly three `regression-corpus` manifests with
eight declared slides and evidence statements.  The public materializer rejects
missing corpus role or slide evidence metadata.  Curriculum and gallery are
separate documentation surfaces whose YAML catalogues reference, rather than
duplicate, declared corpus identity.  The conformance inventory gate currently
reports 8 corpus slides, 3 curriculum links, and 4 gallery links.

No tutorial, gallery, manifest, project, or slide identity selects rendering
policy.  Generated SVG remains materializer-owned byte evidence.

## Verification

- Focused inventory tests: **2 passed**; materializer integration tests:
  **10 passed**.
- Conformance and import-direction gates: passed.
- `pytest -n 4 -q`: **446 passed, 7 skipped**.
- All eight public materializers passed and generated SVG diff is empty.
- Wheel build and isolated installed-wheel smoke: passed.
