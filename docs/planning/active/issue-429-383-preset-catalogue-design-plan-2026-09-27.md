# Design Plan — Preset Catalogue (#429) and the Editorial Preset (#383)

**Public base:** `fea6591a` on `main` (rebased at `2aa0debc`, then `main` advanced with #426's acceptance and a correction while this plan was drafted; re-checked, neither touches presets). **Source of truth:** [Issue #429](https://github.com/tya5/chrona/issues/429), [Issue #383](https://github.com/tya5/chrona/issues/383), [Issue #425](https://github.com/tya5/chrona/issues/425) (the four generated references and their measurements), Specification 62 (`docs/specification/62-declarative-presentation-packages.md`), `src/chrona/resources/presets/` (`library.yaml`, `default.yaml`, `bundles/*`), `src/chrona/usecases/preset_library.py`, `src/chrona/usecases/materialize.py`, `src/chrona/app/cli.py`. **Related, not owned here:** #426 (axis tier appearance — literal criteria met, reopened for a non-literal fold-in tracked as #490), #427/#428/#423/#430/#410/#481/#483/#464 (landed vocabulary this work consumes), #479, #466, #467 (owned elsewhere; named as boundaries below), #490 (Wallboard's own blocker, newly discovered while reading #426).

## Why one plan for two issues

#383's own second comment retitles it: "Build the Editorial preset and make it the bundled default, **as the first entry of the catalogue recorded on #429**." #429's proposal item 2 says the same thing from the other side: "Start with Editorial and make it the default... The padded track lands with it." The two issues describe one piece of work at two grains — #429 is the catalogue decision and order, #383 is the first slice of it — so one design plan, one design, one architecture review and one implementation plan cover both, with #383's literal acceptance treated as the exit criteria for the first implementation slice and #429's as the exit criteria for the whole catalogue. Where they diverge (four presets vs. one) the implementation plan sequences the difference explicitly.

## Published baseline

### The preset contract does not need to change

`presentation-preset-v0.1` (`src/chrona/resources/presets/default.yaml`) already bundles `view`, `theme`, `colorScheme`, `layout` plus `compatibleColorSchemes`. `preset-library-v0.1` (`src/chrona/resources/presets/library.yaml`, `schemas/preset-library-v0.1.schema.yaml`) already lists five unrelated entries — `mission-light`, `control-room-dark`, `print-mono` (View/Theme/Layout owned under `presets/bundles/<id>/`, Color Scheme borrowed from `examples/halcyon-1`), and `executive-light`/`elevated-light` (same shape, borrowing from `examples/controller-z`). `chrona preset copy <id>` (`src/chrona/usecases/preset_library.py::copy_builtin_preset`) already validates and materializes any of the five into editable local files. **None of this is the four #425 directions** — it is an independent, earlier "preset tuning" catalogue (`docs/research/presentation/preset-tuning/<id>/README.md`, commits `07ca0e40`…`b36a0a14`) built by tuning HALCYON-1/controller-z's own Theme per preset. Confirmed by reading `library.yaml` and every bundle's `view.yaml`/`theme.yaml`/`layout.yaml` header (`chrona/view/v0.24`, `chrona/theme/v0.11`, `chrona/layout-profile/v0.9` — current versions, unrelated content).

### The three literal gaps #429 names are real, reproduced on this base

```
$ .venv/bin/chrona preset list
{"status": "failed", "diagnostics": [{"code": "E_COMMAND_SYNTAX", ...,
  "message": "argument preset_command: invalid choice: 'list' (choose from 'copy')"}]}
$ .venv/bin/chrona render --help | grep -- --preset
  --preset PRESET       Presentation preset YAML path; omit it to use bundled
                        chrona-default-draft; explicit resource flags override
                        its members
```
`preset` only has a `copy` subcommand; there is no `list`. `render --preset` only ever takes a filesystem path — the only preset reachable by name is the implicit default reached by omitting the flag. This matches #429's claim exactly.

`default_preset_resource()`/`default_preset_root()` (`src/chrona/resources/__init__.py:67,110`) resolve `presets/default.yaml`'s `body.resources` paths against `examples/halcyon-1`: `view: views/default-draft.yaml`, `theme: themes/briefing.yaml`, `colorScheme: schemes/mission-light.yaml`, `layout: layouts/briefing.yaml`, all inside `examples/halcyon-1`. The bundled default is one example project's own resources, not a designed preset, exactly as #429/#383 state.

### Spec 62 is the wrong authority for this work, and no living spec is the right one

Spec 62 ("Declarative Presentation Packages") is `Status: Proposed`, and §1.1 explicitly forbids resuming its package resolver "before a public reusable corpus direction and a materializer store boundary exist," naming required user-facing operations (`chrona package acquire/inspect/propose-update/materialize`) that do not exist and are not this issue's scope. **The shipped `presentation-preset-v0.1`/`preset-library-v0.1` mechanism this work extends is Spec 62's unstated predecessor** — no living specification currently documents it at all (`grep -rl "presentation-preset-v0.1\|preset-library-v0.1" docs/specification/` returns nothing). The design records this mechanism's current shape and this work's additions as a short addendum to Spec 62 §1.1 (not a new package resolver, not an authorization to build one), so a future Package design has one place that states what already shipped and must migrate cleanly under its §6.

### The corpus-evidence mechanism already reaches a wheel-packaged bundle without new code

The open question going in was how a preset built under `src/chrona/resources/presets/bundles/<id>/` gets *committed, reproducible corpus SVG evidence* — `render` is explicitly "not reproducible evidence" (its own `--help` text), and reproducible evidence comes from an immutable Render Context materialized by `chrona materialize`/`tools/regenerate_public_examples.py`, which resolves `view`/`theme`/`colorScheme`/`layout` references relative to the *project's own store*. Reading `src/chrona/usecases/materialize.py` end to end: `copy_context_closure` (line 164) builds `references = [body[name] for name in ("project", "view", "theme", "colorScheme", "layout")]` and copies each through `_copy_reference` → `_reference_payload` (lines 68–79), which is **generic over reference kind** and already branches on `reference["store"]["provider"] == "package"`, resolving `files("chrona.resources").joinpath(address)` (i.e. straight into the installed `chrona.resources` package, the same root `presets/bundles/` lives under) and requiring an exact `contentIdentity` match. Today this branch is only exercised by font/font-metric locators (`grep -rl "provider: package" examples/*/contexts/` returns only font references), but nothing in the code restricts it to fonts — a Context's `view`/`theme`/`layout` field can use the same `{store: {provider: package, identity: chrona.resources}, address: presets/bundles/editorial/view.yaml, contentIdentity: sha256:...}` shape today. **This means committed corpus evidence for a wheel-packaged preset needs no new mechanism** — just a new Context using an existing, already-generic code path in a way nothing has exercised for these reference kinds yet. This is the central architecture finding of this plan and is spelled out further in the design.

### Vocabulary landed since #425/#429 were filed (re-checked against issue state, not the comment thread alone)

| issue | state | what it gives the four presets |
|---|---|---|
| #410 | **closed** | `letterSpacing`/`textTransform` role properties (`theme-v0.11.schema.yaml:131-132`), measured through Layout |
| #423 | **closed** | `dash` role token wired to `stroke-dasharray` |
| #427 | **closed** | legend miniatures drawn as the real primitive (`swatchInlineSize`, `surface_composer.py:1867-1908`), horizontal (`direction: inline`) legends |
| #428 | **closed** | bare as-of label, label chips |
| #430 | **closed** | `progressInset` role property — padded progress track |
| #481 | **closed** | group bands/headers no longer exclude row stripes |
| #483 | **closed** | readable defaults (axis boundary, dependency arrowheads, print-mono monochrome) |
| #464 | **closed** | glyph gates (milestone shapes beyond the four built-ins) |
| #426 | **open** | View v0.24 per-tier band lane + `typographyRole` **landed** (`b7e29fdc`, acceptance rows 1–4 met per `docs/reviews/current/issue-426-axis-tier-appearance-acceptance-review-2026-09-27.md`); reopened only for a **non-literal** fold-in (alternating/per-interval band fill) now tracked as its own issue, **#490** |

Confirmed directly: `schemas/theme-v0.11.schema.yaml` has `letterSpacing`, `textTransform`, `chipPadding`, `progressInset`, `swatchInlineSize`, `dash`; `presets/bundles/{mission-light,print-mono}/view.yaml` already declare `chrona/view/v0.24`.

### What is explicitly not this work's to touch

- **#479** (open) — project-generic group order from data, palette-by-first-appearance, preset-carried legend `detailProfile`/`visualProfile` preference, `labels: both`. Muted executive's grouped table needs group ordering; §"Muted executive" below states exactly how this plan avoids depending on #479 by scoping order to one fixed corpus fixture rather than claiming project-generic ordering.
- **#466** (open) — annotation placement model. None of the four references need a balloon annotation; not touched.
- **#467** (open) — lane packing as the default row layout, owned by another dev session. None of the four directions' Views declare lane packing (`grouping`/`rowDecoration` only); if #467 lands first and changes default row behavior, the four Views must be re-checked for byte identity before this work's slices land, not the reverse. Sequencing note in the implementation plan.
- **#490** (open) — Wallboard dark's own blocker (per-interval axis fill). Wallboard is sequenced last and blocked on it, exactly as #429's proposal already orders it.

## Literal acceptance, copied verbatim

### #429
> - Four presets ship, each rendering its project through its own View, Theme, Color Scheme and Layout Profile, and each reproducing byte-identically.
> - The bundled default is a designed preset rather than an example project's resources.
> - A preset can be selected by name, and the available presets can be listed.
> - For each preset, the differences between its rendered slide and its generated reference are recorded as named gaps rather than absent.

### #383
> - A preset directory ships in the wheel and `chrona` can resolve a preset from an installed distribution.
> - At least two packaged presets exist, so "switch preset" is a real operation for a user who has only run `chrona init`.
> - An `editorial` corpus example renders reproducibly and its SVG is committed.
> - Every element of the reference specification that could not be expressed is named in the presentation-vocabulary report, with the role or renderer capability it would need.

Note: #383's first two bullets are **already met on `main` today** by the five unrelated bundles (`presets/bundles/` ships in the wheel; `default_preset_resource()`/`builtin_preset_source_root()` resolve from an installed distribution without repository lookup, per #377; five ids exist to switch between). They are not re-litigated; the new work is bullets 3 and 4, plus #429's four bullets which are the harder bar.

## Open decisions for the lead/owner

1. **Default preset identity.** #429 says "replacing `chrona-default-draft`". Keeping the id `chrona-default-draft` while repointing its resources at Editorial would preserve every test/doc that pattern-matches the id string but keep the misleading "-draft" name on a now-designed default. Renaming the id (e.g. `chrona-default`) is the more honest reading of #429 but changes an id string that tests and three docs assert on (`test_draft_closure.py`, `test_cli.py`, `docs/guides/first-project.md`, `docs/design/issue-376-...`, `docs/design/issue-468-...`, `docs/planning/active/issue-483-...`, `docs/reviews/current/issue-377-...`). The design recommends the rename and lists every touched file so the lead can confirm before implementation.
2. **Milestones inside the duration capsule.** #425's Editorial reading: "Milestones live inside the duration capsule... Neither is obviously right, but the reference has an opinion and we currently have a different one by default." The design keeps chrona's existing free-row milestone (no new mechanism) and records the difference as a named gap rather than building capsule-hosted milestones, which is a View/Theme modeling change beyond this issue's vocabulary scope. Flagging for explicit sign-off since #425 called it a real design fork, not just a gap.
3. **Muted executive's group order.** Scoped to the one fixed HALCYON-1 fixture (explicit `grouping.order` list of that fixture's actual field values) rather than claiming project-generic ordering, which is #479's job. This is narrower than "a user's own project can group Muted executive by data" — flagging so the lead can confirm that a corpus-only demonstration satisfies #429's bar for this direction, or decide Muted executive should wait for #479.
4. **Corpus evidence project.** Reusing HALCYON-1 (already the shared fixture for the five existing catalogue entries) rather than a new example project, to keep the new work's surface area to "one more Context per new preset" instead of "one more project." Flagging because #425's generated references all show an 8-row, two-column (Task/Owner) table that HALCYON-1's 26-item fixture does not literally match; the design treats reference fidelity as being about the *visual grammar* (bar treatment, band, legend, dash), not row count, consistent with how the five existing bundles already render HALCYON-1 at 26 rows against references that showed none.

## Slice order (detail in the implementation plan)

1. CLI: `chrona preset list`; `render --preset <name>` name resolution shared with `preset copy`'s existing library loader. Unblocks nothing product-visual but is required by #429 bullet 3 and is independent of every preset's content.
2. Editorial bundle + its own corpus Context/slide + gap report. (#383's exact scope.)
3. Default preset repoint (blocked on decision 1 above) — makes Editorial the bundled default.
4. Technical print bundle + slide (needs nothing beyond landed vocabulary, per #429).
5. Muted executive bundle + slide (needs nothing beyond landed vocabulary; group order scoped per decision 3 above).
6. Wallboard dark bundle + slide — blocked on #490.

Slices 4–6 complete #429's "four presets" bullet; slice 2–3 alone satisfy #383 in full.
