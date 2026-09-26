# Implementation Plan — Preset Catalogue (#429) and the Editorial Preset (#383)

**Design:** [design](../../design/issue-429-383-preset-catalogue-design-2026-09-27.md). **Architecture review:** [review](../../reviews/current/issue-429-383-preset-catalogue-architecture-review-2026-09-27.md). **Approved for implementation** subject to the lead/owner confirming the open decisions named below before the slice that needs them.

## Slice order and dependency

```
I429-1  CLI: preset list, render --preset <name>        (no visual change; independent)
I383-1  Editorial bundle + corpus evidence + gap report  (needs I429-1's resolver, not its CLI surface)
I383-2  Default repoint to Editorial                      (needs I383-1; needs decision D1 below)
I429-2  Technical print bundle + corpus evidence
I429-3  Muted executive bundle + corpus evidence          (needs decision D3 below)
I429-4  Wallboard dark bundle + corpus evidence           (blocked on #490; blocked on naming the
                                                            circle-swatch gap from the architecture review)
```
I429-1 and I383-1 can run in parallel once both are approved; I383-1 is #383's whole scope and closes it on its own once I383-2 lands. I429-2/I429-3 are independent of each other and of I383-2's timing (they do not touch the default). I429-4 is explicitly last, matching #429's own proposal order.

**Re-check before starting any slice:** fetch `main`, confirm none of the four Views' authored row-pitch/mark-height values have been invalidated by #467 landing (architecture review risk 2) and that #479/#466 have not changed `grouping`/annotation semantics underneath this plan. If either has, amend this plan rather than silently absorbing the drift.

## Open decisions requiring sign-off before their slice

- **D1 — decided by the lead 2026-09-27: KEEP the id `chrona-default-draft`.** Only its `body.resources` repoint to the Editorial bundle; no rename. Minimises blast radius against the tests and docs that assert on the id string. §"I383-2" below is updated to this decision; its file list no longer includes id-string edits.
- **D2 — accepted:** milestones stay free-row marks, not nested in the duration capsule; named as a gap in I383-1's acceptance review.
- **D3 — accepted for now:** Muted executive's `grouping.order` is authored as an explicit list of HALCYON-1's own fixture values, not a project-generic capability; named as a gap in I429-3's acceptance review, cross-referencing #479 explicitly, including the note that #479's own I479-1 will later add `grouping.order: {by: earliestPlannedStart}` as the project-generic successor to this scoped list.
- **D4 — accepted:** HALCYON-1 is the shared fixture project for all four new corpus contexts, consistent with the five existing catalogue entries.

**New on `main` since this plan was written — I479-2 (`550f88a5`):** a preset may declare `resources.detailProfile` (kind `review-detail-profile`) and `body.visualProfile: {preferred: <profile>}`, applied unless `--detail`/`--visual-profile` are given. Not required by any of #429/#383's literal bullets, but Editorial's legend is a plausible user of a declared detail profile; each bundle slice below evaluates whether declaring one helps that preset's own corpus evidence and adds it only where it demonstrably does, rather than as an unused schema decoration.

## I429-1 — `chrona preset list` and `render --preset <name>`

**Owned files:**
- `src/chrona/usecases/preset_library.py` — extract `resolve_named_preset_members(identifier) -> dict[str, dict]` (returns `{name: {"bytes": ..., "id": ..., "kind": ...}}`) from `copy_builtin_preset`'s member loop; `copy_builtin_preset` calls it and writes `.bytes` as today. Add `list_builtin_presets() -> list[dict]` (thin wrapper over `_library()` returning `id`/`gallerySet` pairs) for the CLI.
- `src/chrona/app/cli.py` — add `preset list` subparser (no arguments); add name-vs-path branching in `render`'s preset resolution (§1.2 of the design: `/` or `.yaml`/`.yml` suffix ⇒ path, else library lookup ⇒ `E_BUILTIN_PRESET_UNKNOWN` on miss).
- No schema change.

**Tests:**
- `tests/unit/chrona/usecases/test_preset_library.py` (new or extended): `resolve_named_preset_members` returns byte-identical content to reading the packaged file directly, for every current `library.yaml` entry; unknown id raises `E_BUILTIN_PRESET_UNKNOWN`; `copy_builtin_preset` output is unchanged (regression — same bytes on disk as before the refactor).
- `tests/cli/test_cli.py`: `chrona preset list` returns all current entries in file order with correct `gallerySet`; `chrona render --preset mission-light ...` (an existing entry) produces byte-identical Scene/SVG to `chrona preset copy mission-light <tmp> && chrona render --preset <tmp>/preset.yaml ...`; a path containing `/` is never looked up in the library even if it happens to collide with an id (construct a fixture proving the branch order); `--view`/`--theme`/`--scheme`/`--layout` overrides still apply after name resolution.
- Focused run: `tests/unit/chrona/usecases`, `tests/cli`.

**Acceptance:** #429 bullet 3 ("a preset can be selected by name, and the available presets can be listed") — met in full by this slice alone, independent of any new preset content.

## I383-1 — Editorial bundle and its corpus evidence

**Owned files:**
- `src/chrona/resources/presets/bundles/editorial/{view,theme,layout,scheme}.yaml` — new, authored against the design's §3.1 token table and #425's Editorial reading. `view.yaml` at `chrona/view/v0.24`, `theme.yaml` at `chrona/theme/v0.11`, `layout.yaml` at the current `chrona/layout-profile` version, all validated against their schemas before commit (`schema_document`/`Draft202012Validator`, matching the pattern `preset_library.py` already uses for `library.yaml` itself — reuse, do not reinvent, the validation call).
- `src/chrona/resources/presets/library.yaml` — add the `editorial` entry, `gallerySet: generated-design-directions`, all four members' `sourceRoot: presets/bundles/editorial`.
- `examples/halcyon-1/contexts/13-gallery-editorial.yaml` — new Render Context, `view`/`theme`/`layout`/`colorScheme` all `{store: {provider: package, identity: chrona.resources}, address: presets/bundles/editorial/<file>, contentIdentity: sha256:<exact digest>}`, `project` unchanged (HALCYON-1's own project/actual). Compute each `contentIdentity` from the committed bundle file, not by hand — a mismatch is a hard `E_MATERIALIZER_PACKAGE_IDENTITY` failure, which is the intended tamper/drift gate.
- `examples/halcyon-1/manifest.yaml` — add the `gallery-editorial` slide entry (`context`, `expectedSvg`, `expectedScene`), numbered `13-gallery-editorial.svg`/`.scene.json`.
- `examples/halcyon-1/generated/13-gallery-editorial.{svg,scene.json}` — generated, not hand-written.

**Sequencing within the slice:**
1. Author the four bundle YAML files; validate each against its schema directly (`schema_document` + `Draft202012Validator`, ad hoc script or a focused unit test) before wiring anything else — a schema-invalid bundle file must fail loudly here, not three steps later inside `materialize`.
2. Add the `library.yaml` entry; run I429-1's tests against it (proves `chrona preset copy editorial <dir>` and `render --preset editorial` both work) — this is the cheapest way to render Editorial once by hand and inspect it before committing corpus evidence.
3. **Prove the corpus-evidence path** (architecture review risk 3): materialize `13-gallery-editorial.yaml` and confirm `E_MATERIALIZER_PACKAGE_IDENTITY`/`E_MATERIALIZER_PACKAGE_RESOURCE` behave as expected on both a correct and a deliberately-wrong `contentIdentity`, before trusting the mechanism for the remaining three presets. If the theme-inheritance branch (`materialize.py:93-109`) misbehaves for a `presets/bundles/...` address — Editorial's theme is not a derived theme, so this is unlikely to trigger, but check `is_derived_theme(value)` on `theme.yaml` explicitly — fall back to committing a byte-identical copy of the four bundle files under `examples/halcyon-1/{views,themes,layouts,schemes}/editorial.yaml` and referencing those with ordinary `provider: context` locators instead; record the fallback as a design correction if taken.
4. `tools/regenerate_public_examples.py --write --jobs 6`, then `--check`. Attribute every changed file — this slide is new, so its own SVG/Scene are expected; no *other* file should change (Editorial is additive, not a default yet).
5. Render before/after PNG crops for the new slide only (nothing to diff against, since it is new — inspect the rendered PNG against #425's Editorial reference image directly, side by side).
6. Write the **presentation-vocabulary gap report** as a section of this slice's acceptance review: the three named gaps from the design §3.2 (milestone nesting, unmeasured serif, two-line rows), plus any further gap the actual rendered comparison surfaces that the design did not anticipate. This is #383's fourth literal bullet — it must exist even if the list is short, not be silently absent.
7. `tools/diagnostic_inventory.py`, `tools/presentation_contrast.py`, `tools/presentation_font_identity.py`, `tools/presentation_coverage.py` (no `--check`, per the brief's rule, refreshing rather than gating), then `conformance/run_conformance.py`.

**Tests:**
- New unit test asserting all four Editorial bundle files validate against their declared schema versions.
- `tests/integration` / `tests/acceptance/output` — extend whichever test enumerates HALCYON-1's corpus slide count (per the brief's warning that some acceptance tests hard-code corpus counts) to expect 13 slides; state the change explicitly in the slice's review rather than letting a count assertion silently drift.
- Focused: `tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`, plus whichever `tests/acceptance/output` module hard-codes HALCYON-1's slide/label counts.

**Acceptance:** #383 in full — preset directory ships in the wheel (already true; unaffected), at least two packaged presets exist (already true via the five existing entries; Editorial is a sixth), Editorial's corpus example renders reproducibly with its SVG committed, and the gap report names every unreachable reference element.

## I383-2 — Repoint the bundled default to Editorial

**Owned files (D1: id unchanged, resources only):**
- `src/chrona/resources/presets/default.yaml` — `id: chrona-default-draft` unchanged; `body.resources` all repointed at `presets/bundles/editorial/*` (reuse the bundle directly; the default is not a separate copy).
- `src/chrona/resources/__init__.py` — `default_preset_root()` retired only if nothing else needs an `examples/halcyon-1` root once the default no longer resolves there; `default_preset_resource()` unchanged in shape (still resolves `presets/default.yaml`). No id-string edits anywhere — only the resource addresses inside `default.yaml` change, so `default_preset_resource()`'s callers are unaffected in signature.
- `src/chrona/app/cli.py:465-468` — simplify the `_run_render` default branch's root resolution now that `default.yaml`'s members are `sourceRoot`-relative like a library entry.
- `tools/check_starter_perceptibility.py` — update its `default_preset_root()` call site only if that function's return value changes; the id it renders against does not change.
- `tests/unit/chrona/presentation/model/test_draft_closure.py`, `tests/integration/test_onboarding_tutorial.py`, `tests/integration/test_render.py` — update `default_preset_resource()`/`default_preset_root()` *resolution* expectations (new resource paths/bytes), not any id assertion — the id stays `chrona-default-draft`.
- Docs that state the id as fact (`docs/guides/first-project.md`, `docs/design/issue-376-...`, `docs/design/issue-468-...`, `docs/planning/active/issue-483-...`, `docs/reviews/current/issue-377-...`) need **no id edit**; only docs that additionally describe the default's *appearance* (e.g. "the briefing theme") need a note that its resources changed under #383, without touching the id.
- `examples/halcyon-1/views/default-draft.yaml` — no longer referenced by the default preset; check every `examples/halcyon-1/contexts/*.yaml` for `address: views/default-draft.yaml` before deciding whether it stays as a plain corpus View or is removed.

**Every corpus/test render that omits `--preset` changes its rendered appearance.** Before touching code:
1. Enumerate every such call site (`grep -rn "default_preset_resource\|default_preset_root" --include="*.py"` — already enumerated in the design plan's baseline section).
2. Render each affected fixture before and after, and structurally diff Scene JSON (primitive ids moved/added/removed) as the brief's phase-2 rule requires, not just visual inspection.
3. `tools/regenerate_public_examples.py --write --jobs 6`, then `--check`; attribute every changed file to "the default preset changed," which is expected, and separately confirm no *unrelated* file changed.

**Tests:** every test listed above updated to expect the new id/resolution; `tests/cli/test_cli.py`'s default-preset assertions updated; full focused suite re-run.

**Acceptance:** #429 bullet 2 ("the bundled default is a designed preset rather than an example project's resources").

## I429-2 — Technical print

Same shape as I383-1 (bundle files, `library.yaml` entry, one new HALCYON-1 context/slide, gap report), needing nothing beyond already-landed vocabulary per the design's §3 table. No default-preset involvement. Owned files mirror I383-1's list with `technical-print` substituted for `editorial` and slide number `14`.

## I429-3 — Muted executive

Same shape, `muted-executive`, slide `15`. Additionally: author `grouping.order` as an explicit list of HALCYON-1's actual group field values (D3); the acceptance review's gap section must state this scoping explicitly and cross-reference #479 rather than imply project-generic ordering was solved.

## I429-4 — Wallboard dark (blocked)

Not started until #490 (per-interval axis fill) lands. When it does: same shape, `wallboard-dark`, slide `16`; additionally resolve the architecture review's circle-swatch finding — either extend `swatch_geometry`'s dispatch table with a plain-circle bucket (smallest fix, mirrors the existing `milestone`/`mark`/`line`/`legacy` shape) or file it as its own issue if the fix is not as small as it looks once attempted. Do not silently draw Wallboard's seven category swatches as squares and call the direction complete — that is exactly the "quietly avoids the gaps" failure both issues warn against.

## Verification, every slice

- `.venv/bin/python -m pytest -q -n 6 -p no:cacheprovider tests/unit/chrona/presentation tests/integration tests/cli` plus the slice's own owned test dirs.
- `.venv/bin/python conformance/run_conformance.py`; refresh `diagnostic-inventory`/`presentation-contrast` first if stale.
- `.venv/bin/python -m tools.regenerate_public_examples --write --jobs 6` then `--check`; structural Scene diff and attribution for every changed file.
- Before/after PNG crops for the new/changed slide(s), inspected against the corresponding #425 reference image.
- Draft slice review and, at I383-2 and I429-4 (the points where each issue's literal bullets are all met), the literal acceptance review using `docs/reviews/issue-acceptance-review-template.md`, `CI: pending` for the lead to fill in.
