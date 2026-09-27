# Design Amendment — Legend Swatches and Arrangement (#427)

**Amends:** [design](issue-427-legend-swatches-design-2026-09-26.md), [architecture review](../reviews/current/issue-427-legend-swatches-architecture-review-2026-09-26.md), [implementation plan](../planning/active/issue-427-legend-swatches-implementation-plan-2026-09-26.md). **Reason:** lead approval directed no Theme or Layout Profile version bump, and implementation-time inspection found the original dispatch rule (`semantic_binding(role).primitive_kind`) is unsound for at least one role already in the public corpus.

## 1. No schema version bump; both resources extended in place

- **Theme.** `theme-v0.11.schema.yaml` gains `swatchInlineSize` directly in the existing per-role property list (additive, optional), the same way `progressInset` (#430) was added. No new file, no inventory change. The role name `legend-swatch` needs no schema change at all — role names are already open.
  - **Default when absent.** If a Theme declares a `legend` slot but no `legend-swatch` role (or the role exists without `swatchInlineSize`), the inline length of a span/line/decoration-shaped legend swatch falls back to `theme_tokens.text_treatment("legend").font_size * 0.8` — literally today's `legend_size * 0.8` constant — so a Theme nobody has touched keeps its current legend width. The shape and block-size fix (Contract 1/2 below) is not gated behind this default, because it is a correctness fix that uses tokens every such Theme already has (see §2); only the previously-nonexistent *inline length* concept needs a fallback.
- **Layout Profile.** `layout-profile-v0.9.schema.yaml`'s `slot` node gains `direction` (`block`|`inline`, optional), `gap` (optional `distance`), and `itemMinInlineSize` (optional `distance`, `inline` only), in place, meaningful only when `source: legend`. No new file, no inventory change.
  - **Default when absent.** `direction` defaults to `block`. `gap` defaults to `null`, meaning "use today's `legend_size * line_height` step" — i.e. an unmigrated `legend` slot lays out identically to today. `itemMinInlineSize` absent under `direction: inline` means no wrapping (the row grows without bound). A profile that declares neither field is therefore byte-identical in arrangement to before this change; only a profile that adds `direction: inline` (or a `gap`) changes shape.

This replaces every "bump to vNext" instruction in the design, architecture review, and implementation plan documents above. Those documents' *contracts* (what each field means, who owns it) are unchanged; only "new schema file" becomes "new optional field in the existing file."

## 2. Corrected role-dispatch rule

The original design assumed every legend entry's declared `role` is a registered semantic id, so `semantic_binding(role).primitive_kind` could pick the swatch's construction path. This is false for at least `milestone`: the committed Detail Profile (`examples/halcyon-1/profiles/detail.yaml`) declares `{role: milestone, label: Milestone}`, and `milestone` is not a semantic id in `model/semantic_registry.py`, nor does any committed Theme declare a `roles.milestone` block with `markHeight`/`markCornerRadius` (`themes/wallboard.yaml` only binds `colorBindings.milestone.fill: accent`, for the milestone *digest panel*, a different presentation entirely — `layout/surface_composer.py:166,194`). A real milestone point mark on the chart is drawn as source-kind `planned` (or `snapshot`) with `shape="point"` (`layout/surface_composer.py:1182-1188`); there is no separate "milestone" mark geometry anywhere in Layout.

Layout therefore dispatches a legend entry's swatch by a **closed table keyed on the entry's declared role string**, not by the registry:

| Role string(s) | Swatch shape | Geometry source | Notes |
| --- | --- | --- | --- |
| `planned`, `actual`, `snapshot`, `scenario`, `missing-actual`, `progressFill`, `summaryBar` | `mark` (span: Rect; the role's own `markHeight`/`markOffset`/`markCornerRadius`) | the role's own `mark_geometry`/`progress_track`/`summary_bar_height`, exactly as a real mark of that role | unchanged from the design's Contract 1 |
| `milestone` (the one name the corpus and the issue use for a point/diamond key) | `point` (Symbol, `rounded_diamond_path`) | `theme_tokens.symbol()` (the same `milestoneSymbol` token every point mark on the chart already uses) for shape; `mark_geometry("planned")` for height — a milestone point mark is drawn with the `planned` (or `snapshot`) role's own height ratio, so borrowing it is literally "the size the chart draws it", not a new convention | satisfies acceptance item 1 without requiring a `roles.milestone` block in any Theme |
| `asOf`, `dependency`, `dependency-critical` | `line` (Path, marker/dash from the role) | the role's own `strokeWidth`/`dash`/`marker` | paint/pattern keyed by `semantic_binding(role).scene_role` (e.g. `as-of` for `asOf`) so a legend line resolves through the exact same theme lookup the real stroke uses, not a re-derived alias |
| `calendarClosed` | `decoration` (Rect, `tokens.background`) | the role's own background treatment | unexercised by the current evidence slice but kept for completeness |
| anything else | today's fixed square `Rect` at `legend_size * 0.8`, stacked as before | — | the explicit compatibility fallback the lead's approval requires; a Detail Profile can still legend an arbitrary paint-only role and get exactly today's behavior |

`semantic_binding(role)` is still consulted, but only to resolve the *paint* role (`scene_role`) for the registered cases, not to select the primitive kind. `Contract 1`/`Contract 5` in the design document are read as amended by this table; nothing else in the design changes.

## 3. Implementation-plan slice I427-1 is replaced

I427-1 no longer creates `theme-v0.13.schema.yaml`/`layout-profile-v0.10.schema.yaml` or edits `schema-inventory-v0.1.yaml`. It instead:

- adds `swatchInlineSize` to `theme-v0.11.schema.yaml`'s existing role property list;
- adds `direction`/`gap`/`itemMinInlineSize` to `layout-profile-v0.9.schema.yaml`'s `slot` node (conditional on `source: legend`, all optional);
- adds the role-dispatch table above to `model/semantic_registry.py` or `layout/surface_composer.py` (a private mapping, not a schema);
- keeps `legendEntry.theme_role → "legend-swatch"` and the `legendLabel` split (design Contract 5), used only where the dispatch table's geometry source needs a distinct size/spacing lookup from the label's `legend` role.

I427-2 through I427-5 are unchanged in intent; I427-2/3's "Focused tests" gain one more case: an unregistered legend role falls back to today's square, byte-identical.

## 4. Public-evidence scope, restated

Unchanged from the design/plan: `02-programme-board` (existing `wallboard.yaml` legend: shape/size fix for `planned`, `actual`, `milestone`) and a new legend on `03-launch-campaign` (`print-portrait.yaml`/`print.yaml`, `direction: inline`, entries `planned` (already `pattern: outline` in `print.yaml`), `dependency`, `asOf`). No other committed example has a `legend` slot, so no other theme needs `legend-swatch` or a Layout Profile arrangement field, and no other public SVG is expected to change.
