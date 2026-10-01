# Issue #718: Target Parts Catalogue, Architecture Review

**Decision:** Accept the design with three conditions (C1 to C3 below). No decision needs a core change, so the
issue stays at depth C. One part of the issue's table, seigaiha, is dropped from the new catalogue for a reason
that is a schema limit, and two groups (frames, stamps) are catalogued without a role that can paint them; both are
stated, not hidden.

Reviewed: [design plan](../../planning/active/issue-718-target-parts-catalogue-design-plan-2026-10-02.md),
[design](../../design/issue-718-target-parts-catalogue-design-2026-10-02.md), against `main` observed 2026-10-02,
[Spec 64](../../specification/64-portable-icon-catalogs.md) section 8, [Spec 07](../../specification/07-style-and-theme.md)
section 5.2, `schemas/theme-asset-source-v0.1.schema.yaml`, `schemas/icon-catalog-v0.4.schema.yaml`,
`chrona.presentation.icons.importer` and `normalizer`, the builtin preset library, and the 14 target pages.
Checked by running the importer on a draft source and rendering every candidate glyph and pattern through
`chrona render` with a scratch Theme. Not checked: how a future role will place a frame or stamp, and the look of a
part inside a finished preset (none binds one yet).

## Boundary audit

| Boundary | Decision | Result |
| --- | --- | --- |
| Asset -> Theme | geometry only; colour, dash, outline treatment, glow stay Theme-owned | Preserved: parts carry no colour field, and the importer has none to carry |
| Catalogue -> importer | a new `theme-asset-source` document, imported by the existing command | Preserved: no importer branch, no schema change |
| Catalogue -> preset library | not pinned or bound; `library.yaml` unchanged | Preserved (D6) |
| New set -> starter | separate set, separate id, no edit of pinned bytes | Preserved (D1) |
| Frames and stamps -> consumers | glyph entries with no role that paints them | **Gap, recorded** (F1) |
| Pattern tile -> adapter | tile-clipped, rotated about the tile centre | Preserved with an authoring rule (F3) |
| Gallery -> product | an evidence script reading shipped bytes, writing next to the research documents | Preserved (D7) |
| Licence -> notice | original geometry, MIT, notice in catalogue and `.NOTICE`, hashes in the manifest | Preserved (F5) |

## Findings

**F1. Frames and stamps have no consumer (accept, record, do not fix here).** A catalogue glyph is selectable only for
the three milestone symbol roles. A scroll frame, a clipping edge, a panel corner or a seal stamp cannot be placed
on an annotation, title or panel by any Theme today. Spec 64 section 5 refuses valid-but-unreachable *schema forms*;
this is a catalogue resource, not a schema form, and the entries are reachable as gate glyphs (checked), but it is
the same smell at resource level. The remedy is not here: a role that places a catalogue glyph on a surface is a Theme
schema change owned by #584 (per-kind stamp) and #587 (repeated-glyph border, panel corners). Keeping the entries is
right: the issue's acceptance asks for them or a reason, the extracted and licensed geometry is the reusable value, and
a future role then has assets to bind. Mitigation (C1).

**F2. The importer cannot produce vector `icons` (accept).** Frames and stamps could be `icons`, which a View
`visuals` request can place beside a label. The v0.4 schema retains them, but `import_theme_assets` writes `icons: {}`.
Adding the branch changes the importer, which is core. The design correctly stops at glyphs and names the gap; if #584
prefers `icons` it opens that importer work itself and the entries are re-issued in a new catalogue version.

**F3. Pattern geometry must survive tile clipping (accept with an authoring rule).** An adapter serializes a pattern as
a clipped repeat, so a stripe centred on the tile edge would paint half its width and an edge line would vanish. The
design centres hatch and hazard stripes and doubles the lattice edge lines on both tile edges. The scratch renders
through the product show continuous stripes and a continuous honeycomb. The rule belongs in the manifest notes so a
later author does not "simplify" it away.

**F4. Seal stamps are decorative geometry (accept).** A glyph has no alternative text. A seal beside an annotation must
not carry meaning alone; #584 owns the kind label and text that make the stamp redundant. The design's stamp strokes
stay legible at about 20 px in the gallery; at 13 px the character blurs, which is acceptable for a decorative mark.

**F5. Provenance of the seals (accept).** The characters are drawn as original monoline skeletons from the structure of
`危` and `記`; the bundled Noto Sans JP was a visual reference and no outline was copied. Letterform structure is not
protected expression, a hand-drawn skeleton is independent work, and the alternative (font outlines under OFL with a
reserved-name and notice burden) contradicts the issue's "original work, MIT". Residual risk is low and is stated in the
notice and the design.

**F6. Overlap with the starter (accept).** Five gate names (`diamond`, `hexagon`, `lantern`, `pin`, `star`) exist in both
sets. Both are namespaced, so there is no collision, but a reader could pick the wrong one. The manifest and the gallery
state that the starter holds the simple builtin forms and this set holds the targets' drawings with outline twins.

**F7. Seigaiha is a real schema limit (accept the drop).** The pattern grammar has no per-primitive substrate fill,
occlusion or clip, and an arc must have its centre inside the tile. Overlapping occluded scales therefore cannot be
written. An approximation would misrepresent the target; the starter's seigaiha is the shipped answer. A faithful one
needs an occluding or clipped primitive, which is a schema change and is left to a successor if the owner wants it.

**F8. Identity and packaging (accept).** The importer writes the catalogue with a temporary file whose mode is `0600`;
the committed file mode is set to the usual `0644`, and git carries only the executable bit. The catalogue and source
are about 31 KB together against a 5,000,000 byte wheel budget; the exact wheel size before and after is part of the
implementation evidence. A regeneration test keeps the catalogue equal to its source.

**F9. Parallel work (accept).** The change adds new files and one appended section per target README. The agents working
on named date ranges (#582), the axis (#492) and the legend lane (#497) own other files; no source, schema or example
file is shared. The README sections are self-contained appends to limit conflicts.

## Conditions

- **C1.** The manifest records, for each entry with no consumer, `consumer: none-yet` with the knob issue that owns it
  (#584 or #587), and the gallery and READMEs say the same. No preset binds such an entry.
- **C2.** An integration test renders a Theme that binds a catalogue glyph and a catalogue pattern through the real
  product, so an entry that stops being accepted fails CI, not a user.
- **C3.** The acceptance review rows for the catalogue say `met` only for what the importer and the render evidence
  show; seigaiha and the unconsumed frames and stamps are stated with their successors.

## Conclusion

The design keeps the catalogue in the resource layer, adds no role, schema or importer branch, and records the two
gaps it cannot close. The accepted extension points are a frame/stamp role (#584, #587) and an occluding pattern
primitive; neither is needed to ship the parts that exist.
