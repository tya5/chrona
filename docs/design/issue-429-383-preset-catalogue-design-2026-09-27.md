# Design — Preset Catalogue (#429) and the Editorial Preset (#383)

**Plan:** [design plan](../planning/active/issue-429-383-preset-catalogue-design-plan-2026-09-27.md). **Inputs:** #429, #383, #425 (generated references and measurements), Specification 62, `src/chrona/resources/presets/`, `src/chrona/usecases/preset_library.py`, `src/chrona/usecases/materialize.py`, `src/chrona/app/cli.py`. **Scope:** name/list a builtin preset; build the Editorial preset and make it the bundled default; specify Technical print, Muted executive and Wallboard dark to the same contract so #429's catalogue bullet is complete on paper even though only Editorial is this phase's committed implementation target; record every unreachable reference element as a named vocabulary gap.

## 1. Selecting and listing a preset by name

### 1.1 `chrona preset list`

New subcommand under the existing `preset` parser (`src/chrona/app/cli.py:369`), reading the same `library.yaml` the `copy` subcommand already validates (`_library()` in `preset_library.py:23`). No new schema. Output, matching the CLI's existing JSON-diagnostics convention:

```json
{"status": "ok", "presets": [
  {"id": "mission-light", "gallerySet": "halcyon-mission-brief-appearance"},
  {"id": "editorial", "gallerySet": "generated-design-directions"}
]}
```
One row per `library.yaml` entry, in file order (the schema already requires unique `id`s, so no sort ambiguity). `gallerySet` is exposed because it is the only human-facing classification the schema currently carries; it is not the Design-Space discovery classification Spec 62 §2.1 describes for a future registry, and the design does not add one here — a bare id/gallerySet pair is the smallest thing that answers "what presentations are there," which is the literal bar.

### 1.2 `render --preset <name>`

`render --preset` (`cli.py:274`) currently only accepts a filesystem path; `_run_render` (`cli.py:465-468`) loads it as a preset YAML document with members resolved relative to the preset file's own directory (or, for the omitted case, relative to `default_preset_root()`). Adding name resolution needs a **third resolution shape**, because a `library.yaml` entry's four members may each live under a *different* `sourceRoot` (e.g. Editorial's view/theme/layout under `presets/bundles/editorial/`, its colour scheme wherever it is decided to live — see §4), unlike a preset file's members, which are conventionally siblings on disk.

**Design:** extract the member-loading loop already inside `copy_builtin_preset` (`preset_library.py:71-96`) into a shared function that returns the four resolved, validated, in-memory documents plus their resource kind/id, without writing anything to disk:

```python
def resolve_named_preset_members(identifier: str) -> dict[str, dict[str, Any]]:
    """Validate and decode one builtin preset's four members in memory."""
```
`copy_builtin_preset` becomes a thin wrapper: call `resolve_named_preset_members`, then write each decoded-and-reencoded... no — **write the original bytes**, not a re-encoding, to preserve today's guarantee that `preset copy` reproduces the packaged file byte-for-byte. So the shared function must return the raw bytes alongside the decoded document (decode only for the `id`/`kind` validation already performed), and `copy_builtin_preset` writes the raw bytes as it does today; `_run_render`'s new path decodes the same bytes it would otherwise read from a file path, so the render path is byte-for-byte what `preset copy <name>` followed by `--preset <path>` would produce, which is the byte-identity #429 asks for.

`render --preset VALUE` resolution order, decided once at CLI parse time and unambiguous because the two syntaxes cannot collide (`library.yaml`'s `id` pattern `^[a-z][a-z0-9-]*$` never contains `/` or a `.yaml` suffix, and a real preset file path always does in every existing usage):
1. If `VALUE` contains `/` or ends in `.yaml`/`.yml`, treat it as a path (today's behavior, unchanged).
2. Otherwise, look it up in `library.yaml`. Found → resolve in memory via `resolve_named_preset_members`. Not found → `E_BUILTIN_PRESET_UNKNOWN`, the diagnostic `copy_builtin_preset` already raises, reused rather than inventing a second spelling.

This keeps `--preset` a single flag (no new `--preset-name`), keeps the path branch's behavior and diagnostics completely unchanged, and adds the name branch as a strict superset. `--view`/`--theme`/`--scheme`/`--layout` continue to override individual members after either resolution, unchanged (`cli.py:274`'s existing "explicit resource flags override its members").

## 2. The bundled default becomes a designed preset

`default.yaml`'s `body.resources` today point at `examples/halcyon-1`'s `views/default-draft.yaml`, `themes/briefing.yaml`, `schemes/mission-light.yaml`, `layouts/briefing.yaml` (via `default_preset_root()`). This design repoints all four at the Editorial bundle (`presets/bundles/editorial/{view,theme,layout,scheme}.yaml`) and drops `default_preset_root()`'s dependency on `examples/halcyon-1` — the wheel-owned default no longer needs an example project's directory at all once Editorial is bundle-owned. `default_preset_root()` (`resources/__init__.py:110`) is retired; nothing outside `default.yaml`'s own resolution used it except the render CLI's `preset_root=None if args.preset else Path(str(default_preset_root()))` (`cli.py:468`), which becomes unnecessary once the default's members carry `sourceRoot`-relative paths the same way a `library.yaml` entry does — i.e. the default is re-expressed as reusing the exact same resolution the name-based preset path uses (§1.2), not a bespoke `preset_root` concept. This removes a second code path rather than adding one.

**Id.** Recommend renaming `chrona-default-draft` → `chrona-default`, per decision 1 in the design plan; implementation plan enumerates every touched file. If the lead prefers to keep the id and only repoint resources, that is a one-line change to this section with no other consequence — flagged as the reversible part of this design.

**Public-visible consequence, stated plainly:** every corpus/test/doc render that omits `--preset` changes its rendered appearance completely (Editorial's warm-paper/navy/coral palette, capsule bars, two-tier band, replacing HALCYON-1's `briefing` theme). This is the intended effect of #429/#383, not a regression, but it means the implementation plan's public-evidence step must diff and explain every changed file, not just the ones that "should" change (AGENTS.md's standing rule).

## 3. What each of the four directions needs, and what it does not

Per #429's own table, all four differ in **View** (grouping, table columns, row marks), so each is a genuine preset, not a Theme swap over one View. All four need the same three landed capabilities (per-tier axis appearance, legend miniatures, dash), already shipped. Beyond that:

| direction | View decisions | extra capability | status |
|---|---|---|---|
| Editorial | no grouping; Task/Owner-initials table; one capsule mark with an inset fill | `progressInset` (#430) | landed |
| Technical print | no grouping; numbered rows; outline `planned` + inset `actual` + red overrun | — (mark-height/offset/paint-order, #398, already shipped) | none |
| Muted executive | group header rows; numbered rows; solid bar + dashed baseline offset above (`markOffset`, negative) | group order (scoped, §5) | landed vocabulary; scoped View authoring |
| Wallboard dark | no grouping; category mark in a table cell (`visualEncodings target: cell`); one solid capsule per team | per-interval axis fill | **blocked on #490** |

None of the four needs a new Scene primitive, a new pattern kind, or a renderer change. This is the "bar vocabulary is finished" and "most of the rest already works" finding #425 recorded independently of this design; re-confirmed here against the schemas listed in the design plan.

### 3.1 Editorial — token targets from #425's measurement

Authored as Theme/Layout values against the measurements #425 already took (not re-derived here):

| token | target | source |
|---|---|---|
| `timeline.mark.blockSize` ÷ row pitch | 0.50 | #425 stage-2 reading |
| `planned` role `markGeometry` fill ratio | 0.60 (centred) | #425 stage-2 reading |
| progress-track inset | 6–7 px left, 5–6 px top/bottom, expressed as `progressInset` ratio of mark block size | #425 Editorial reading |
| quarter band | 50 px, `#2f455d` fill, white label | #425 Editorial reading |
| month band | 45 px, `#e3e5ea` fill, navy label | #425 Editorial reading |
| today marker dash | ~9 on / 7 off | #425 Editorial reading |
| today label | bare `TODAY`, above the plot only (not through the axis band) | #428 |
| table header / axis labels / legend labels | uppercase, ~0.15–0.25em positive letter-spacing | #410's own measurement on #383 |
| legend | horizontal, 6 entries, each the real primitive (capsule outline, coral capsule, diamond, elbow+arrowhead, dashed segment, grey rect) | #427 |

Bar-to-row proportion (0.50) and the specific colour values are ordinary Theme/Layout authoring under landed schemas — no mechanism gap. This table is the phase-2 authoring reference; it is not itself the YAML.

### 3.2 Where Editorial still falls short, named rather than absorbed

Per #429/#383's shared rule, every place the built preset cannot reach the generated reference is a named gap, not a workaround:

1. **Milestones inside the duration capsule.** The reference nests a milestone diamond inside the same capsule as its duration bar; chrona's milestone is a free mark on the row. Kept as chrona's existing behavior (decision 2 in the design plan); named as a gap rather than modeled as a new nested-mark relationship, which is a View-model change beyond this issue.
2. **Serif display headline.** #425's own regeneration note: the Editorial prompt's "serif display headline" conflicted with "no caption on the image" and the model dropped the serif; the sheet's own measurement cannot settle a serif token. Recorded as unmeasured rather than guessed at — Editorial's slide title uses the same sans family as the rest of the direction until a corrected reference sheet exists.
3. **Two-line table rows** (from the stage-1 sheet, not stage 2, but on the same reference lineage) — a chrona table cell is one text primitive; not attempted, already related to #403 per #425's own note.

These three, plus any further ones the implementation phase's side-by-side comparison surfaces, go into the "presentation-vocabulary report" #383 asks for — a short section of the slice's acceptance review, not a new document type, mirroring how #425 itself recorded gaps as issues rather than as a separate report artifact.

## 4. Resource ownership: bundle-owned, not example-borrowed

Following the *later* precedent in the existing catalogue (`presets: give <id> its own tuned View, Theme and Layout`, e.g. `3ce2f9ba`) rather than the earlier one that borrowed a corpus project's files: each of the four new directions owns its View, Theme, Layout **and now also Color Scheme** under `src/chrona/resources/presets/bundles/<id>/{view,theme,layout,scheme}.yaml`. Unlike the five existing entries, none of the four new palettes (warm paper/navy/coral; black/white/red; near-black + six category hues; warm greys+blue+amber) is a generic reuse of an existing corpus scheme, so borrowing one would be a false economy — each is genuinely new and belongs with its preset. `library.yaml` gains four entries with `sourceRoot: presets/bundles/<id>` on all four members, matching the shape already used by `mission-light` for its non-scheme members exactly, extended one field further.

IDs, chosen to avoid colliding with the five existing entries: `editorial`, `technical-print` (not `print-mono`, which already exists and is a different direction), `muted-executive` (not `executive-light`), `wallboard-dark` (not `control-room-dark`).

## 5. Committed corpus evidence without a new mechanism

Confirmed in the design plan: `materialize.py::copy_context_closure` copies `view`/`theme`/`colorScheme`/`layout` references generically (`materialize.py:171`), and `_reference_payload` (`materialize.py:68-79`) already branches on `store.provider == "package"`, resolving `files("chrona.resources").joinpath(address)` and pinning an exact `contentIdentity`. A new Render Context can therefore reference `presets/bundles/editorial/{view,theme,layout,scheme}.yaml` directly:

```yaml
view:
  id: chrona-preset-editorial
  kind: view
  store: {provider: package, identity: chrona.resources}
  address: presets/bundles/editorial/view.yaml
  revision: {token: chrona-preset-editorial-v1}
  contentIdentity: sha256:<view.yaml's exact digest>
```
No code change to `materialize.py`, no schema change (`render-context-v0.16`'s `store`/`revision` fields are already untyped provider-specific objects). This is the same shape today's contexts already use for font/font-metric locators, applied to a reference kind nothing has exercised it for yet. One new context per new preset (`examples/halcyon-1/contexts/13-gallery-editorial.yaml`, numbered after the existing twelve), reusing HALCYON-1 as the shared fixture project exactly as the five existing catalogue entries already do, added to `examples/halcyon-1/manifest.yaml`'s `slides` list with an `expectedSvg`/`expectedScene` pair like every other slide. `gallerySet: generated-design-directions` in `library.yaml`, distinguishing it from the existing `halcyon-mission-brief-appearance`/`controller-z-treatment-ladder` sets.

This choice is deliberately conservative: it makes "committed, reproducible SVG" true using the ordinary regression-corpus pipeline (`tools/regenerate_public_examples.py`, `conformance/run_conformance.py`), rather than the ad hoc PNG-screenshot evidence the five existing catalogue entries settled for (`docs/research/presentation/preset-tuning/*/README.md`, which is not corpus-verified and drifts silently). That gap in the existing five bundles is noted for the lead as a pre-existing shortfall this design does not fix, since fixing it is not in either issue's literal acceptance and would expand scope.

## 6. Muted executive's group order, scoped

Muted executive's View groups rows under header rows (`presentation: header`, the same mechanism `mission-light`'s tuned View already uses on the same HALCYON-1 fixture). `grouping.order` takes an explicit list of field values (`docs/research/presentation/preset-tuning/mission-light/README.md`'s own recorded gap: "a project-generic preset cannot know the values"). This design authors that explicit list against HALCYON-1's own known group values for the corpus context only — the preset remains project-generic in the sense that a *different* user project supplies its own `grouping.order` (or falls back to alphabetical, as `mission-light` already does), but the packaged preset itself does not claim to solve data-derived ordering. #479 owns that. Named explicitly as a gap in the acceptance review, cross-referenced to #479 rather than re-filed.

## 7. Specification update

Add to `docs/specification/62-declarative-presentation-packages.md` §1.1 a short paragraph recording: (a) the shipped `presentation-preset-v0.1`/`preset-library-v0.1` mechanism and `chrona preset copy`/`chrona preset list`/`render --preset <name>` are the pre-Package predecessor this specification's future resolver must migrate cleanly (§6's promise already covers this in principle; this makes the concrete predecessor legible); (b) `library.yaml` now carries nine entries across two unrelated catalogues (`halcyon-mission-brief-appearance`/`controller-z-treatment-ladder` tuning, and `generated-design-directions`, the #425-sourced set), and a future package's discovery classification (§2.1) is not the same thing as `gallerySet`, which stays catalog-internal. No normative behavior in Spec 62 itself changes; this is a status/predecessor note, not a new authority claim, consistent with the specification's own §1.1 caution against introducing "a parallel public authoring path."

## 8. Layer-ownership check

- **View**: grouping, table columns, row-mark composition, axis tiers — all four directions' differences live here, as #429 already established.
- **Theme**: paint, typography (`letterSpacing`/`textTransform`), dash, progress inset, legend swatch sizing — all named token targets in §3.1 are Theme values, none is a new Theme *capability*.
- **Layout**: unchanged; slot allocation and geometry computation are not touched by any of the four directions' authored values.
- **Scene/adapters**: unchanged; no new primitive, no new SVG emission branch.
- **CLI/usecases**: `preset list`, `render --preset <name>` resolution, and the `resolve_named_preset_members` refactor are the only code changes; they add no policy, only name-to-resource resolution, matching the CLI's existing role.

No boundary crossing found; nothing here needs a layer to gain authority it does not already have.
