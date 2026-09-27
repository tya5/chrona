# Design Correction — Candidate Placement Rebased on Current `main` (#466)

**Corrects:** the [candidate design](issue-466-candidate-placement-design-2026-09-26.md) and the [C2–C4 plan](../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md), as the handoff required ("choose the next free version and publish any necessary correction first"). **Base:** `main` at `16b0011d`. **Handoff:** owner-approved takeover by the dev B session, 2026-09-27.

## 1. View version: the next free one, a single live version

The design names `chrona/view/v0.23` and keeps "v0.22 … a separately validated legacy input". Two facts on `main` change this:
- View v0.23 is #428's as-of `date` form, and #426 and #467 take the following versions.
- The repository keeps **one live View version**. `contracts/resources.py` maps only the live version, the predecessor is `transitioning` in the schema inventory, and every shipped View migrates at a bump.

**Corrected:** candidate authoring lands in **the next free View version at landing**, copied from the then-live schema. The old rung spelling (`callout.placement`, the `rail`/`above`/`below`/`start`/`end` ladder) **remains valid in that version** and normalizes, through C1's typed expansion, to exactly today's candidates. So every migrated View keeps its bytes, which is C1's accepted byte identity. `candidates` is the new, additive spelling. A View uses one spelling per annotation, never both. This replaces "v0.23 does not carry the old spelling" and "v0.22 remains a separate legacy input". No behaviour of an unmigrated annotation changes.

## 2. Theme: `annotationContainer` in Theme v0.11, not a new version

`chrona/theme/v0.12` is the existing *derived-Theme* (inheritance) schema, not a successor of v0.11, so the design's "Theme v0.12 adds `annotationContainer`" would collide with it. The repository extends Theme v0.11 in place with additive optional role properties (#430 `progressInset`, #428 `chipPadding`).

**Corrected:** the `annotationContainer` token type (`outline: rectangle | balloon`, corner radius, tail base width in em) and its binding on annotation box roles are added to **Theme v0.11** as optional. Themes without it are unchanged byte for byte. Derived v0.12 Themes may replace an existing binding as usual. #465 (an image behind an annotation container) will extend the same token with image and inset fields, so the value keeps a closed `outline` discriminator.

## 3. Adjacent work since the design

- **#467 lane rows:** lane names are phase-1 required text ([#467 phase correction](issue-467-lane-rows-phase-and-version-correction-2026-09-27.md)). Balloons and leaders are phase 4 and already avoid them through the one index.
- **#428 label chips:** chips are label backgrounds; balloons are annotation containers. There is no shared role or code path, and no conflict.
- **#488:** member-label row containment is a placement-region rule and a natural candidate-model consumer (region = own row band). It stays a separate issue.
- **#483:** the dashed as-of line (`dash.as-of`) is a Path rule. The "same side of the as-of rule" constraint applies unchanged.

## 4. Unchanged

The candidate grammar (region, search, obstacles, connector), the bounded nearest-free search, the atomic box plus connector commitment, Project-note references, the balloon geometry ownership, the acceptance rows and the C2–C4 slice boundaries are unchanged.
