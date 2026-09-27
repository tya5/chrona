# Implementation Plan — Group Bands and Headers (#481)

**Public design base:** the commit that publishes the [architecture review](../../reviews/current/issue-481-group-bands-and-headers-architecture-review-2026-09-26.md). **Authority:** [design](../../design/issue-481-group-bands-and-headers-design-2026-09-26.md), Specification 45 (Group headers), Specification 50 §3.4, [Issue #481](https://github.com/tya5/chrona/issues/481).

## Literal acceptance ledger

1. "Row stripes and group bands can be combined across the whole surface: stripes above group bands, or group bands as outlines or header-only."
2. "A group's band includes its own header row, under both `all` and `alternate`."
3. "`group-header:*` text uses the Theme's `groupHeader` role; a test asserts the declared weight."

## Coordination

No other open issue touches `surface_composer.py`'s background-shape or group-header code. Before each push, fetch `origin/main`, check ahead/behind and the staged file list, and stop on a conflict in `layout/surface_composer.py`.

## I481-1: row stripes paint above group bands

**Owners/files:**
- `layout/surface_composer.py::compose_surface_layout`: reorder the group-band/header-band loop before the row-stripe loop.

**Focused tests:**
- a combined-surface case (`rows: alternate`, `groups: all`, `rowBand`/`groupBand` extent `both`, distinct Theme colors for `row-band`/`group-band`): the Scene primitive order/paint order places the striped row's shape above the group band it overlaps at the same declared `backgroundPaintOrder`;
- an unstriped row under the same config still emits (and is not occluded by) the group's own band shape;
- `_validate_background_shapes` still rejects a genuinely overlapping translucent pair (regression guard: order change must not weaken this check).

**Public evidence:** `tools.regenerate_public_examples --write` then `--check`. Expected: **no byte change** — no shipped preset combines `groupBand: both` with `rowBand: both` today. Any change must be attributed or is a defect.

**Gate:** focused tests (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`), conformance, 21 materializers, then push and the four-job CI.

## I481-2: a group's band includes its own header

**Owners/files:**
- `layout/surface_composer.py`: the group-building loop (`content_bounds` folds in the header block when present); the shape-emission loop (`groupHeaderBand` gated by `group_decoration == "none"` or the same `banded` selection as the body band).

**Focused tests:**
- `groups: all`, headered: a group's `groupBand` shape bounds contain its `groupHeaderBand` shape bounds;
- `groups: alternate`, headered: a selected group's `groupBand` bounds contain its own header; an unselected group emits neither `groupBand` nor `groupHeaderBand`;
- `groups: none`, headered: every group still emits `groupHeaderBand` (header-only technique unaffected);
- canvas/viewport union (`_completed_canvas`) is unchanged in outcome (still contains every shape) with the expanded `content_bounds`.

**Public evidence:** batch of all 21. Expected: every preset combining a header presentation with `groups: all|alternate` and a non-`none` `groupBand` shows its `groupBand` `Rect`'s block-start move up by `timeline.groupHeader.blockSize`; row/mark/table geometry unchanged. Attribute every changed shape; inspect before/after PNGs for at least `control-room-dark` and one light preset.

**Gate:** as I481-1.

## I481-3: `group-header:*` text uses the `groupHeader` role

**Owners/files:**
- `layout/surface_composer.py`: the group-header `place_text` call (`typography_role="groupHeader"`, `semantic_id="groupHeader"`, baseline from the `groupHeader` role's own font size).
- `src/chrona/resources/presets/bundles/elevated-light/theme.yaml`, `.../executive-light/theme.yaml`: add a `groupHeader` typography role (reusing `weight.regular`/`size.body`, matching current visual intent) and a `groupHeader.fill` color binding.
- `examples/aster-ssd/themes/executive-light.yaml`, `examples/aster-ssd/themes/onboarding-variation.yaml`, `examples/controller-z-ja/themes/executive-light.yaml`, `examples/orion-asic/themes/orion-light.yaml`, `examples/controller-z/themes/executive-light.yaml`, `examples/controller-z/themes/elevated-light.yaml`, `examples/controller-z/themes/material-icons-light.yaml`: same addition, matched to each file's existing token names.

**Focused tests:**
- a Theme declaring `groupHeader.fontWeight` distinct from `text`'s weight: the `group-header:*` Scene primitive's completed weight equals the declared `groupHeader` weight, not `text`'s;
- a Theme without a `groupHeader` role: group-header placement raises `E_THEME_ROLE_REQUIRED` at `/body/roles/groupHeader/fontFamily` (regression guard against a silent fallback);
- full focused suite (`tests/unit/chrona/presentation`, `tests/integration`, `tests/cli`) green with all nine Theme files updated in the same commit as the code change (no intermediate red commit).

**Public evidence:** batch of all 21. Expected: `group-header:*` text weight/size changes for `control-room-dark`/`mission-light`/`print-mono` (bold, as already declared); new `group-header:*` primitives for `elevated-light`/`executive-light` at `weight.regular` (no visible weight change, only an explicit role now driving them). Inspect before/after PNGs for `control-room-dark` and `elevated-light`.

**Gate:** as I481-1.

## I481-4: issue acceptance

Separate acceptance review under `docs/reviews/current/`, one row per literal criterion, test links, CLI output for both reproductions (stripe/band combination; alternate header containment; weight assertion), the three slices' batch diffs, and the green four-job CI run. Close #481 only then.

If a slice exposes a Theme file beyond the nine listed, a shape whose containment the batch diff cannot attribute, or a conflict with the other dev session's row/annotation work, pause, publish a design correction, and amend this plan.
