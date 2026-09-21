# Color Scheme Authoring

**Status:** Design complete; implementation not started.  
**Owns:** Versioned Color Scheme resources, Theme color-intent bindings, color resolution, and accessibility validation.

## 1. Authority

Color Scheme owns concrete colors only. Theme retains typography, spacing, stroke, marker, pattern, opacity, text alternatives, and the mapping from a visual role to a closed color intent. Style continues to select roles from facts; Layout continues to own geometry; Scene and adapters consume concrete paint only.

A Color Scheme MUST NOT select facts, roles, geometry, output capabilities, or a renderer fallback. A scheme choice therefore changes color values only.

## 2. Resource

The resource is `chrona/color-scheme/v0.1`, validated by `schemas/color-scheme-v0.1.schema.yaml`. It has no inheritance, aliases, expressions, or implicit base scheme. Its canonical identity is the SHA-256 of canonical JSON of the whole resource (sorted keys, UTF-8, no insignificant whitespace).

`body.colors` is a closed map of concrete CSS `#RRGGBB` values: `surface`, `surfaceRaised`, `text`, `textMuted`, `accent`, `positive`, `negative`, `warning`, and `neutral`. `body.category` is a non-empty ordered sequence of concrete colors. `body.suitability` declares intended `background`, `colorVision`, and `print` use. `body.provenance` records `kind`, `source`, and `license`; a built-in scheme lacking all three is invalid.

The initial resource contains no external palette bytes. A future external built-in requires exact source and redistribution terms in `provenance`; a familiar palette name is insufficient evidence.

## 3. Theme v0.2 binding and literal removal

M25 replaces the legacy `chrona/presentation/v0.1` Theme resource with `chrona/theme/v0.2`, defined by `schemas/theme-v0.2.schema.yaml`. Its `body.values` may contain only non-color typed values; its `body.roles` binds non-color properties; its existing `body.metrics` retains source-measurement token bindings; and its required `body.colorBindings` maps every color-bearing role property to one closed Scheme intent. A Role name may use the existing `group:<stable-key>` form. No Theme inheritance, alias, or partial overlay survives the replacement.

There is no literal-color escape hatch in the shipped M25 authoring path. An earlier proposal to retain one would create a second concrete-color authority and prevent a Context from guaranteeing a coherent scheme. Existing literal-color Theme examples are migrated atomically when M25 becomes reachable; no compatibility loader remains.

## 4. Context and resolution

`chrona/presentation/v0.5` Render Context requires immutable `theme` and `colorScheme` references. Resolution is exactly:

1. validate Context, Theme, and Scheme resource shapes and references;
2. validate the Theme binding set against the closed intent vocabulary;
3. validate Scheme provenance and all required text/background contrast pairs;
4. resolve each Theme color binding from the Scheme and retain all non-color Theme values unchanged, producing an internal concrete Theme;
5. measure sources, resolve Layout, compose Scene, and serialize Output.

No renderer, Layout adapter, or Scene constructor may read a Scheme resource or supply a color default. A gallery is multiple independent Context evaluations with one distinct `colorScheme` reference per result.

`chrona render-review-gallery` receives two or more immutable Context references plus
the same snapshot-root and Store identity inputs as `render-review`. It resolves every
closure before writing output, rejects duplicate Scheme content identities with
`E_SCHEME_GALLERY_DUPLICATE`, sorts results by `(colorScheme.id, contentIdentity)`, and
writes one `<colorScheme.id>.svg` file per result to an empty output directory. It does
not merge Scenes, mutate Contexts, or pass a renderer override. A write failure leaves
no success manifest; a successful `gallery.json` records the ordered Context and Scheme
identities plus output filenames.

## 5. Categories and variants

For category key `k`, the palette index is the unsigned first eight bytes of `SHA-256(scheme-content-identity + "\\0" + k)` modulo `len(category)`. It is independent of View order, source iteration, and renderer state. A finite palette may repeat a color for distinct keys; category color is never the sole differentiator.

Light/dark and print/high-contrast alternatives are separate immutable Scheme resources, not mutable variants or automatic host inference. A user selects the resource explicitly in Context. `suitability` is a declaration, not a license to remove markers, patterns, or text alternatives.

## 6. Accessibility and diagnostics

For each pair `(text, surface)` and `(text, surfaceRaised)`, the resolver computes WCAG relative luminance and requires contrast >= 4.5:1 for normal text. If a future Theme declares a large-text role, that role may use >= 3:1. Color distinction alone never satisfies a semantic requirement.

Required stable diagnostics are `E_SCHEME_SCHEMA`, `E_SCHEME_PROVENANCE`, `E_SCHEME_INTENT_UNKNOWN`, `E_SCHEME_THEME_BINDING`, `E_SCHEME_CONTRAST`, and `E_CONTEXT_COLOR_SCHEME`. Diagnostics name the resource ID and path and never recover with a default.

## 7. Acceptance invariants

1. The same closed Context produces identical concrete colors and category indices.
2. Reordering groups does not change a category key's index.
3. Switching Scheme does not change facts, selected roles, geometry, metrics, Scene structure, or target capability requirements.
4. Missing provenance, unknown intent, missing binding, and insufficient contrast fail before Scene emission.
5. Markers, patterns, and text alternatives remain available after every scheme change.

## 8. Replacement boundary

The M25 `render-review` runtime accepts only Theme v0.2 and Context v0.5. Theme v0.1 and Context v0.4 are deleted from that presentation entry point in one migration. The separate core `chrona render` diagnostic SVG is outside M25 and is not a Scheme-capable presentation path. This is intentionally not a compatibility release: a stale review resource diagnoses rather than being upgraded or rendered with fallback colors.
