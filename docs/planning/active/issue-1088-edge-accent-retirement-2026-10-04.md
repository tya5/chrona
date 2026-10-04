# Issue #1088: retire the annotation-kind content-box edge accent — design plan

**Phase:** pre-design; no behavior or schema decision is approved.  
**Public baseline:** `main` at `cc6baa905325620cb0f47761e0717c7b0a252f2a`.  
**Issue/claim:** [#1088](https://github.com/tya5/chrona/issues/1088), [current claim](https://github.com/tya5/chrona/issues/1088#issuecomment-5979213999).  
**Predecessor:** #1049 added a start-border path but retained the content-box accent to preserve current Theme output.

## Published baseline

- #1088 requests migrating corpus Themes with `edge` to `annotationContainer.border.start` using `paint: kind`, regenerating/reviewing grouped output and images, then removing the schema declaration, kind-frame branch, and role contract with a migration note.
- Issue #1088 is open; no decision comments preceded the linked dev-A claim. PR #1061 is also open against the same `main` commit.
- Literal acceptance: (1) “no corpus Theme declares `edge`”; (2) “the accent branch of the kind frame is gone”; (3) “S0 gate and corpus diff reviewed.”
- Five Theme files declare edge tokens: Halcyon `wallboard-annotation-kinds`, `target-b`; Controller Z `annotation-kinds`, `annotation-artwork`, `viewer-fit`. The last two values appear unused and still matter to criterion 1.
- PR #1061 is open and owns target-B. It already migrates to `note-container.border.start {width: 3, paint: kind}` and removes its edge token. Do not edit that Theme until reconciling its merge and generated evidence.
- Runtime ownership: token parse/resolution in `src/chrona/presentation/model/theme_tokens.py`; accent geometry in `src/chrona/presentation/layout/annotation_kind_frame.py`; shared border strip geometry in `annotation_border.py`. Review but retain `side_strip` if still used for borders.
- `annotation-kind-accent.fill` remains used by kind-painted borders; its fill/color binding is distinct from optional `.edge`. Do not remove the role or binding without evidence.
- Authored Theme v0.11 is transitioning to v0.13 (`issue-496-theme-v0.11-retirement`); v0.13 is live. Derived Theme v0.14 is a separate wrapper. Dispatch is `contracts/resources.py`; inventory is `schemas/schema-inventory-v0.1.yaml`.

## Questions for design and architecture review

- Removing an accepted Theme field/value may invalidate or change resources. Resolve versioning under Spec 56 §§3.1–3.2; do not edit v0.13 in place or silently ignore old `edge` declarations.
- Decide whether a successor authored Theme version is sufficient or derived Theme inheritance/dispatch also changes. Verify against resolver behavior and v0.14 examples rather than assuming paired version numbers.
- Determine a safe v0.11/v0.13 migration and retirement boundary: staged legacy support or first-party migration followed by retirement when Spec 56’s no-reference condition holds. Confirm support expectations.
- Verify whether generic token type `edge` has consumers beyond this accent; separate deleting the token kind from deleting the role member if ownership requires it.
- Review geometry without assuming parity: old strip is inside the content inset; border is on the outline edge. Check paint, inset, full-length side, contrast, and kind semantics.
- Review the whole path: Theme ingress/resolution → Layout geometry → Scene identity/paint → SVG/PNG adapters, schema registry/diagnostics, and generated-example gates.

The intended user-visible outcome is a kind-colored border on the declared note edge, not an inset content stripe. Review content, box geometry, kind identity and unrelated Theme choices; document intentional inset/extent changes rather than promise old box geometry or conceal differences with spacing changes.

## Dependencies and proposed slices

1. **Reconcile prerequisites:** inspect #1130’s published state and #1061’s merge plus derived output; refresh `origin/main` before decisions.
2. **Publish design/review:** select the version and retirement contract, migration effects, layer ownership, and tests; review against Specs 07/56 and #1049 before code.
3. **Migrate corpus:** update issue-owned remaining Themes, remove unused edge values, regenerate via public materializers, and leave target-B with its owner.
4. **Remove capability:** after approval, update schemas, registry/inventory, Theme token contract, and kind-frame geometry; preserve kind fill for borders. Add focused schema/resolution/geometry tests.
5. **Acceptance:** run S0 schema-equivalence, conformance, focused tests, and affected materializers; review grouped Scene/SVG/PNG diffs, diagnostics, IDs, contrast/perceptibility, and each literal criterion.

## Evidence required before design approval

- Confirm all five declarations, role bindings, other source/test Theme fixtures using `edge`, and whether v0.14 replacements can express the old field.
- Show the proposed registry/inventory path for v0.11, v0.13, and derived v0.14, including any unsupported-version outcome.
- Identify tests proving the accent is absent, border geometry/paint remain correct and intentionally distinct, and unrelated Theme output is unchanged.
- Name the exact public materializer set and grouped visual-review method; derived outputs must be reproducible, never hand-edited.
- Keep compatibility and migration questions open until evidence resolves them; a passing S0 gate or grep alone is not acceptance.

This record is only the design-plan slice. The next publication is the reviewed design and architecture decision; implementation planning and edits follow that approval.
