# Design — Exact Multi-Face Font Measurement (#448)

**Design plan:**
`issue-448-exact-multi-face-font-measurement-design-plan-2026-09-26.md`.

## Decision

All text geometry is measured by a closed `FontMetricsCatalog`, selected with
the completed Theme treatment's primary `(family, weight)` pair. The immutable
Context path already has this model. Draft `--system-fonts` will adopt the
same model: it resolves every distinct pair used by the resolved Theme into an
exact, identity-pinned `SystemFontFace`, turns every face into metrics, and
exposes a catalog plus its matching `FontFile` set for one draft render.

There is no regular-face default, synthetic bold, nearest-weight selection, or
per-call host lookup. A requested pair that cannot be resolved exactly rejects
before Layout. Layout remains host-independent: it receives only the catalog
and its selected metric. A completed `TextPlacement` keeps the selected
metric's source content identity, and a PNG renderer receives exactly the
catalog's matching font files.

## Draft resolution model

`DraftFontResolution` changes from a one-face wrapper to a catalog closure:

```text
DraftFontResolution
  metrics: FontMetricsCatalog
  font_files: tuple[FontFile, ...]
  faces: tuple[SystemFontFace, ...]     # diagnostic/runtime provenance only
```

All tuples are sorted by normalized primary family and numeric weight. The
constructor rejects duplicate logical pairs and divergent duplicate identities.
No host path appears in a Render Context, Scene, or serialized artifact; paths
remain volatile renderer inputs just as they are for the existing one-face
draft route.

`_draft_system_font_resolution` derives its request set from every resolved
Theme role that carries the complete typography binding. It resolves each pair
once using the existing exact system resolver, creates each entry with the
existing byte-identity check and metrics import, then constructs the catalog.
An empty or invalid Typography Theme, missing face, changed bytes, or duplicate
catalog key is a closure error before measurement. The existing diagnostics
remain the boundary vocabulary: `E_FONT_SYSTEM_MISSING` for an unavailable
exact requested face and `E_FONT_SYSTEM_MISMATCH` for an invalid or substituted
result. Missing catalog selection continues to use `E_FONT_METRICS_UNAVAILABLE`;
it cannot fall back.

## Measurement and projection

The generic Layout contract stays `metric_for_role` / `metric_for_family`. It
selects `FontMetricsCatalog.select` when given a catalog and retains the
test-double path for single metric fixtures. Each of `measure_sources`, table
allocation, wrapping, ellipsis, axis labels, annotations, and `place_text`
therefore reaches the exact face through one selector rather than carrying a
parallel face switch. Scene remains a projection of completed placements and
does not resolve fonts.

The public Scene contract is unchanged: `textLayout.family`, `weight`, and
`assetIdentity` are already completed placement facts. The release checker
will audit those three facts against the immutable Context catalog and reject
an unavailable pair or mismatching identity. This audits evidence, not Theme
source, and therefore protects the Layout-to-Scene boundary.

## Target delivery

SVG continues to serialize the completed family and weight. The Draft PNG
adapter receives `DraftFontResolution.font_files`, which contains every exact
face used by the Theme, and keeps `skip_system_fonts=True`. It has no reason
to discover or substitute a font. Immutable Context rendering continues to
obtain the same complete asset set from its declared descriptor. PDF and
typeset targets remain excluded from `--system-fonts`, preserving their
existing immutable/reproducible closure requirement.

## Corpus and acceptance evidence

The checked audit enumerates every committed Scene text primitive, derives the
Context's declared `(family, weight) → font identity` mapping, and verifies
that the primitive's `assetIdentity` is that mapping's exact value. It emits a
deterministic, role-independent diagnostic for a missing mapping or identity
mismatch. The generated report records the number of weight-700 placements
and confirms zero measurements against a 400 identity.

Focused system-font fixtures use two distinct installed fixture faces for one
family, set a Theme role to 700, and prove that Layout records each face's
identity while PNG receives both files. A missing bold fixture rejects before
Layout. Public corpus regeneration and the checked report prove the three
#448 acceptance statements without treating a visual diff as a font-identity
oracle.

## Exclusions

- No arbitrary family aliases, CSS fallback stacks, variable-font axis
  interpolation, synthetic styles, or host-font discovery in immutable
  rendering.
- No Scene schema version change: the required completed identity fields exist.
- No renderer-side geometry, font metrics import, or font selection.
