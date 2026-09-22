# Issue 99 Step 4 — Schema/Contract Correction

**Status:** Proposed correction to the typed-closure design.  **Affected plan:**
`issue-99-typed-contracts-design-plan-2026-09-22.md` (PR #115) and C99-4A
(PR #116).

## Trigger

During C99-4A verification, the public `aster-ssd/overview` materializer was
rejected before rendering.  Its declared `chrona/view/v0.1` resource uses:

```yaml
visibility:
  relations: {mode: semantic, overflow: suppress}
```

The existing v0.1 schema permits only the legacy string enum, although the
existing v0.5 content normalizer already implements the object form and public
generated SVG evidence depends on it.  The earlier closure loader checked only
a version prefix, so this schema/resource drift remained hidden until the
schema-first contract boundary made it observable.

## Decision

The schema remains the only authority for acceptance.  Do **not** relax the
contract parser, retain a prefix-only fallback, or convert malformed data after
validation.  Instead, correct the published `view-v0.1` schema to express the
already-public v0.1 relation-visibility form:

- retain `none`, `semantic`, and `all` string values;
- additionally accept an object with required `mode` and `overflow` fields;
- constrain `mode` to the existing v0.1 supported values (`none`, `semantic`)
  and `overflow` to the already-implemented (`suppress`, `diagnose`) policy.

This is a schema conformance correction, not a resource version migration.  A
v0.2 migration would require fields and policy that those valid v0.1 public
resources do not declare, and would falsely present an acceptance repair as a
product-policy upgrade.

## Cross-design review

| Boundary | Result |
| --- | --- |
| Schema → contract | Strengthened: the exact schema now accepts precisely the public syntax used by the runtime. |
| View → normalization | Preserved: no normalization policy changes; its existing object-form handling remains the sole interpretation. |
| Layout / Scene / renderer | Preserved: no geometry or SVG serialization change. |
| Public materializers | Preserved: the correction restores their current materializability and requires byte identity. |
| Issue #99 C99-4A | Unblocked: `ViewContract` can validate both materialized v0.1 and v0.2 declarations without parser fallback. |

## Implementation and acceptance

One correction PR will modify the v0.1 schema and add a schema acceptance test
that validates every declared public v0.1 View (after canonical YAML scalar
normalization).  It must also run the public materializers and confirm no SVG
diff.  Once merged, C99-4A resumes from its preserved implementation state;
the temporary implementation must be rebased on the correction and retested.

No other View v0.1 surface syntax, schema version, resource declaration, or
generated artifact is in scope.  Discovery of another public schema/resource
drift reopens this correction before C99-4A implementation continues.
