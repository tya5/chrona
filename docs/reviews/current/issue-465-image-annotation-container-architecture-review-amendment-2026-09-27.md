# Architecture Review Amendment — Ambiguity 1 Resolved (#465)

**Corrects:** the [architecture review](issue-465-image-annotation-container-architecture-review-2026-09-27.md)'s
"Reviewed ambiguities and resolutions" item 1 and its whole-system table row
for "Icon catalogs / Specification 64". **Resolves against:** the
[design amendment](../../design/issue-465-image-annotation-container-design-amendment-2026-09-27.md).
**Decision:** design approved for implementation, unconditionally.

## Resolution

Ambiguity 1 asked whether "the store to reuse" meant the icon catalogue's
*engineering pattern* (a new sibling resource kind) or the icon catalogue
*itself* (extend `chrona/icon-catalog/v0.3`). The lead has resolved this:
reuse the icon catalogue itself. A raster PNG entry may serve as container
artwork for a Theme `annotationContainer` binding (Specification 64 §7,
added by the design amendment); arbitrary artwork otherwise stays excluded.
No new resource kind, schema, or Context input.

**Consistency re-check under this resolution:**

| Boundary | Result |
| --- | --- |
| View | Unchanged conclusion. "A View cannot bind it" holds because no View field reads `annotationContainer`, not because of where the asset is stored. A View and a Theme can now name the *same* catalog entry for two unrelated purposes (icon companion; container backdrop) without either purpose leaking into the other's schema. |
| Icon catalogs / Specification 64 | The reserved-family clause ("a future multicolour logo or image belongs to a separately designed asset family") is narrowed by a scoped exception (§7) rather than exercised: #465's artwork is a purpose-built PNG entry already inside spec 64's existing "does not own... arbitrary" carve-out language, used by a second consumer. This is a smaller change to spec 64 than a new sibling specification would have been. |
| Context | No `render-context` version change. `inputs.iconCatalogs` closure, already verified before Theme/Layout, is the only closure #465 depends on. This removes the architecture review's original "Context has bumped five times... ordinary" justification as moot — there is no bump to justify. |
| Theme/Layout/Scene/adapters | No change from the original review; Contracts 2–4 were already noted as independent of which reading of ambiguity 1 was chosen. |

No unresolved architectural question remains for #465.
