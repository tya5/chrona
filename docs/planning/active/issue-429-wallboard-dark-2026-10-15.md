# Issue #429, slice I429-4: the Wallboard dark preset (work record)

Living record. Public base: `c62cff3d0` on `main`. Reference: the Wallboard dark prompt on #425 (copied in #429's body). Refs #429.

## Baseline

- The catalogue lists editorial, technical-print, marquee, sunday, target-b and muted-executive (library.yaml); `wallboard-dark` is absent. An older bundle `control-room-dark` exists with a different design; its id is not reused.
- #490 (axis band `fillScale`, Spec 60 section 7) is closed; #479, #486, #426 are closed. The vocabulary below exists on main.
- Literal acceptance this slice serves (#429): four presets ship, reproduce byte-identically (row 1); a preset is selectable by name (row 3); the reference differences are recorded as named gaps (row 4).

## Design: vocabulary per treatment

| Reference treatment | Layer | Vocabulary used |
| --- | --- | --- |
| Near-black ground, alternating row bands at about 4% white | Scheme + View + Theme | Scheme `surface`, `surfaceRaised`; View `backgroundDecoration: {rows: alternate}`; Theme `row-band.fill: surfaceRaised` |
| Table with a header row, Task and Owner, no rules | View | `tableColumns` with `title` and `{field: owner}` (a field key, no value); no `row-rule` role |
| One solid capsule per owning team | View + Theme | View `colorEncoding: {scale: series, target: planned, source: {field: owner}, domain: firstAppearance}`; Theme `colorScales.series.palette` over six Scheme categories; `planned` with `markHeight/markOffset` tokens and a fully rounded `markCornerRadius` |
| Large filled chevron milestones | Theme | `milestone-symbol` shape `chevron` |
| Thick orthogonal connectors with solid arrowheads | Theme | `dependency` stroke 2, solid `arrow` marker |
| Bright today line with a label chip | Theme/Scheme | `as-of.stroke: accent`; the chip and a date-less label are not reachable (gap) |
| Quarter band with a fill per interval, each month a darker tint of its quarter | View + Theme + Scheme | two band tiers, quarter and month, each with `fillScale` (#490): the quarter tier keys `alternating`, the month tier keys `alternating` through `containingTier: 0`; Theme `colorScales` map the keys to Scheme categories (quarter hue; its darker tint) |
| Large bold month labels | Theme | `axisMonth` / `axisQuarter` typography roles at weight 700 |
| Legend strip | Detail Profile + Layout | Planned, Milestone, Dependency, Today, Non-working day |

## Named gaps

Recorded in [wallboard-dark-vocabulary-gaps.md](../../diagnostics/wallboard-dark-vocabulary-gaps.md). The principal one: a fill per calendar quarter (blue, green, brown, purple) is not reachable by a generic preset. An `interval` key is the window-relative ordinal of every retained interval, and the Theme mapping must name the whole domain exactly (no recycling), so it would fix the window length; `alternating` is the key that holds for any window, giving two quarter hues, with each month its quarter's darker tint. No capability was invented and no design YAML or `examples/**` was edited.

## Slice plan and evidence

Files: `presets/bundles/wallboard-dark/{view,theme,scheme,layout,detail}.yaml`, a `library.yaml` entry (appended), `docs/guides/first-project.md`, the CLI characterization golden, `tests/integration/test_wallboard_dark_preset.py`, and the loop-style tests that every builtin preset must satisfy (counts, and the named exclusions each recorded as a gap). No schema is touched. A gallery slide (`examples/**`) is reviewer work and is not part of this slice.
Evidence: the full local set (`tests/integration`, presentation, tools, cli, usecases, public examples check) run in the worktree before pushing.
