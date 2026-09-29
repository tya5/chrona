# #496 design amendment: builtin catalogue copy and preset rendering

**Amends:** [selected design](issue-496-theme-asset-catalogues-design-2026-09-28.md), Slice 3. **Review:** [whole-architecture review](../reviews/current/issue-496-builtin-catalogue-copy-architecture-review-2026-09-29.md). **Implementation:** [Slice 3 plan amendment](../planning/active/issue-496-builtin-catalogue-copy-implementation-amendment-2026-09-29.md). **Normative predecessor:** [Spec 62](../specification/62-declarative-presentation-packages.md).

## Scope and selected behavior

The #496 issue remains open, has no later comments, and its literal Slice 3 acceptance remains:

> “A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags.”

> “A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile.”

Advance the finite wheel-owned preset library to `preset-library/v0.2`. Each entry keeps its four ordinary members and optional detail profile, and may add `members.iconCatalogs[]`. Each catalogue member has exactly `id`, `kind: icon-catalog`, `sourceRoot`, `sourcePath`, `noticeSourcePath`, `contentIdentity`, and `noticeContentIdentity`; the identities are `sha256:<64 lowercase hex>` of the exact catalogue and notice bytes. Catalogue IDs are unique within an entry. `sourceRoot: icons` is an admitted packaged root, not a filesystem search. The importer-validated catalogue `id` and `kind` must match the member. The `.NOTICE` bytes must equal the catalogue's declared complete licence notice; missing or mismatched notices fail as `E_BUILTIN_PRESET_NOTICE`, and other missing/identity mismatched members fail as `E_BUILTIN_PRESET_RESOURCE` before any destination write. Existing `presentation-preset/v0.1` already carries `iconCatalogs` and `detailProfile`, so it remains unchanged.

The starter catalogue is original Chrona geometric artwork under MIT, not copied third-party art. Package its source, normalized `icon-catalog/v0.4`, complete `.NOTICE`, and a provenance manifest pinning exact source/catalogue/notice SHA-256 and the seven-glyph/six-pattern inventory. The library entry pins the catalogue and notice. Rehome any currently example-owned generic scheme into the wheel bundle byte-identically before adding asset bindings, so builtin closure does not depend on Controller-Z example facts. The generic starter preset uses an admitted Rect fill pattern and a #464 catalogue glyph; its existing review-detail profile supplies the legend. No asset is bound to `annotation-note-box`, and the bundle adds no domain-specific project facts.

`chrona preset copy <id>` copies exactly the declared ordinary members, each catalogue to `catalogs/<id>.yaml` and notice to `catalogs/<id>.NOTICE`, and the detail profile into an empty destination. The generated preset retains exact catalogue and detail references; all members are preflighted before the first write. It retains the current refusal for a nonempty destination. `chrona render --preset <name-or-path>` resolves that same declared closure automatically; rendering needs no `--icon-catalog` or other asset flag. An explicit `--icon-catalog` list replaces, rather than silently augments, the preset catalogue list under the existing CLI override rule. It does not scan sibling resources, consult a registry, or infer members from Theme contents.

## Boundaries and failure behavior

The preset library owns wheel distribution membership and copy addressing. Catalogue import owns canonical asset data and licensing; Theme owns selection and role paint; presentation closure verifies the exact pinned catalogue before Layout; the existing detail-profile path owns legend content. Copy is a deterministic materializer, not a second resolver. Render uses the materialized preset's declared closure and reports the established asset-reference diagnostic with exact Theme pointer and `set:name` if resolution fails.

This does not implement Spec 62 acquisition, locks, package manifests, package-to-package dependencies, or registry behavior. Spec 62 may treat the catalogue as an ordinary verified static member only under its future separately approved resolver. The `icon-catalog` resource kind, Context closure, and `presentation-preset/v0.1` are not migrated by this amendment.

## Acceptance evidence

Slice acceptance requires inventory and provenance for all seven glyphs and six pattern entries; exact source/catalogue/notice identities; copied-tree identity and reference checks; and a copied preset rendered by the public `--preset` path without extra flags. Inspect completed Scene plus actual SVG and decoded PNG for glyph, pattern, and legend visibility. Test missing member, wrong identity, absent notice, and nonempty destination failures. This amendment authorizes planning and implementation of that slice only; it does not claim acceptance.
