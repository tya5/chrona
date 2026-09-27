# Example Reproducibility and Context Materialization

**Status:** Design complete — Issue 38
**Depends on:** Render Context v0.5/v0.6 and Specification 38.

## 1. Version policy

The public materializer accepts immutable Render Context v0.5 and v0.6. These are the only current Context versions. v0.5 remains supported for existing materialized examples; v0.6 is the current form for row-composition examples. No v0.4 test/schema compatibility is retained.

## 2. Immutable closure materialization

Materialization is a test/example adapter, not a new runtime authority. For locally stored references, it copies each pinned resource into the directory named by that reference's own revision token and address. For package or other provider-backed resources that cannot be represented by that local revision store, it may stage verified bytes in a transient, disjoint execution-overlay namespace keyed by the full authored reference or asset-locator identity. That physical staging choice does not change the logical reference: provider identity, address, opaque revision token, and authored content identity remain intact, and the staged bytes must be exactly those resolved through that reference. In either case, materialization never replaces a declared revision with a primary revision, copies an embedded schedule payload, or resolves a latest resource. For v0.6 `inputs.snapshot`, it copies both the snapshot-ref resource and its nested Project reference, each at their declared revisions.

## 3. Context identities and expected SVG

Example Context files are derived immutable closure manifests. Any change to a referenced byte sequence requires updating its content identity and regenerating the expected SVG through the public CLI. The acceptance test validates every top-level and input reference, including colorScheme. Hand editing an expected SVG is not a generation path.

## 4. Verification and CI

The acceptance Context test selects the schema by Context version. Integration tests materialize every manifest slide through `render-review`, compare its expected SVG byte-for-byte, and prove mismatch detection. CI runs this integration suite. A materialization failure is a release failure.

## 5. Historical evidence

The three empty M27 documents are recovered only by verifying their exact historical non-empty blob/content identity. If no such verified content is accessible, they remain documented as unavailable rather than invented. The milestone ledger's current status must be regenerated only as a current operational record, never presented as historical review evidence.

## Boundary review

- Context owns immutable references; local resources are copied into their declared revision namespaces, while provider-backed resources may be exposed through a transient identity-keyed overlay without rewriting those references.
- CLI and closure validate/consume Contexts; they do not generate example authority.
- Examples own manifests and expected artifacts.
- CI owns reproducibility enforcement.
- No legacy Settings/Theme contract, mutable fallback, or project-specific branch is introduced.
