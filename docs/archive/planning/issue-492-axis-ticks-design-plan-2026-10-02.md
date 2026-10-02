# Design Plan — Axis Ticks at Interval Starts (#492)

**Public base:** `4981db0a` on `main`. **Source of truth:** [Issue #492](https://github.com/tya5/chrona/issues/492) (body only, no comments at 2026-10-02), [Specification 39](../../specification/39-axis-and-observation-clarity.md) ("Axis lanes, cells and rule (#426)"), [#426 cells correction](../../design/issue-426-axis-cells-correction-2026-09-27.md), Specification 56 section 3.2. **Related:** #426 (closed; filed this as row 10), #453 (target gap map), #493 (two labels per cell, a different mechanism; see decision 5). Targets: Flat Pack, Off-World, Swiss, Marquee, Montmartre under `docs/research/presentation/*-target-2026-09-26/`.

## Published baseline, inference, and unverified facts

Read at `4981db0a`:

1. **Grid tiers draw full-height lines only.** `layout/surface_axis.py`, the `grid-major`/`grid-minor` branch of `compose_axis`, emits one `Path` per interval start from `timeline.bounds.block` through the whole plot block size, with semantic id `axisGrid` or `axisGridMinor` (Theme roles `axis-major` / `axis-minor`, both `_PATH_PAINT` only in `scene/capabilities.py`). A View can declare a week `grid-minor` tier (the unit and role enums allow it), so the interval starts exist; only the extent is fixed.
2. **No Theme property can shorten a tick.** The Theme role property list (`schemas/theme-v0.11.schema.yaml`, `theme-v0.13.schema.yaml`) has paint and the #426 geometry properties (`laneBlockSize`, `cellGap`, `labelInset`) and nothing for a mark length on an axis Path role.
3. **The axis slot is a Theme metric.** `timeline.axis.blockSize` fixes the slot height; a tick must fit inside it (as lanes must; #426 review, "Limitation").
4. **Scene and adapters need nothing new.** `scene/v05_builder.py` projects any `axisGrid` Path from the points Layout completed.
5. **Targets (inferred from the committed mocks, not from text):** Off-World's README row "HUD ruler" names "week ticks" under tier appearance (#426); the Swiss mock shows short vertical marks at the starts of the quarter and month cells. The Flat Pack, Marquee and Montmartre rows do not mention ticks in text; the issue body groups them, and that grouping is an unverified inference.
6. **Unverified:** how a derived Theme's pinned identities are produced for a committed example (resolved in the implementation plan).

## Literal issue acceptance ledger (copied verbatim)

1. A tier can draw ticks of a Theme-declared length at its interval starts, including a week tier, and one committed slide shows them.

## Use cases and decisions to close

1. **Short ticks for a week tier** on a mission axis (Off-World), under a month tier that keeps full separators.
2. **Same View, two Themes:** a Theme that wants a boundary mark at every interval start decides whether it is a full line or a short tick.
3. **Decision 1, where the intent lives.** Options: (A) a new View tier role `tick` (View schema widening); (B) a Theme property on the existing grid roles. Leaning B: the View already says "a mark at each interval start" (`grid-*`); how far the mark extends is appearance, owned by the Theme.
4. **Decision 2, tick geometry.** Origin (the axis rule, the slot bottom, growing toward the slot top), length bound (must fit the slot), invalid values (diagnosed, not ignored), and whether a tier at an unaligned window start draws a tick.
5. **Decision 3, schema.** The added Theme role property is optional and behaviour-preserving, so it follows Specification 56 section 3.2 (in place, no version bump, S0 gate recorded in the PR).
6. **Decision 4, the committed slide.** A new slide beside Controller Z `axis-tiers`; no existing slide or corpus data is edited.
7. **Decision 5, #493.** Decide after the design whether two labels in one cell share this mechanism.

## Responsibility and architecture review questions

- Theme declares the length, Layout completes the Path, Scene and adapters unchanged: confirm no Scene or adapter work.
- Does a Theme property that changes what a View-declared `grid-*` tier looks like break "View selects, Theme paints"? (The tier still names where; the Theme names how far.)
- Byte identity: a Theme without the property must render exactly as today; every committed Theme is untouched.
- Failure behaviour: a tick longer than the slot, and a non-positive length.
- Role admission (`scene/capabilities.py`) must admit the property on exactly the two grid roles.

## Ordered design slices and evidence needed

1. **Design plan** (this file).
2. **Design** with the Specification 39 amendment, and the owner-decision comment on the issue.
3. **Architecture review.**
4. **Implementation plan.**
5. **Implementation** (one code PR): schema property in place, S0 gate, capability admission, Layout, synthetic tests with mutation check, the committed slide with regenerated evidence, a rendered-image check.
6. **Acceptance review** with the exact-main three-OS run.

Acceptance evidence: a synthetic Layout test per behaviour (ticks, byte-identical default, bounds, invalid), the S0 gate result, the committed slide's SVG viewed, and the literal acceptance row above.
