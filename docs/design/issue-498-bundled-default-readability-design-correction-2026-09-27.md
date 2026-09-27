# Design Correction — Bundled Default Readability (#498)

**Status:** selected behavior correction, subject to its linked whole-architecture review and implementation-plan amendment.
**Issue and owner direction:** [#498](https://github.com/tya5/chrona/issues/498), [owner decision](https://github.com/tya5/chrona/issues/498#issuecomment-5852117933).
**Baseline design:** [selected design](issue-498-bundled-default-readability-design-2026-09-27.md).
**Baseline review:** [architecture review](../reviews/current/issue-498-bundled-default-readability-architecture-review-2026-09-27.md).
**Baseline implementation plan:** [implementation plan](../planning/active/issue-498-bundled-default-readability-implementation-plan-2026-09-27.md).
**Successors:** [whole-architecture review amendment](../reviews/current/issue-498-bundled-default-readability-architecture-review-amendment-2026-09-27.md) and [implementation-plan amendment](../planning/active/issue-498-bundled-default-readability-implementation-plan-amendment-2026-09-27.md).

## Reason for correction

The selected design chose `labels.content: [title]` to keep plot member names visually separate from finish-variance facts. Read-only candidate renders exposed a consequential existing Layout rule that the earlier design did not record: when `finishDelta` is absent from `labels.content`, Layout emits a separate `variance:<row>:<object>` label for each combined row with a known finish delta. When `finishDelta` is present, Layout appends the delta to the member-label text and omits that independent variance label. The two declarations therefore change both visual encoding and placement; this is not merely a choice of label wording.

The correction makes the separation explicit. The selected default uses title-only member labels and keeps finish-variance labels as independent Layout output, with their existing variance semantic roles, placements, and overflow behavior. These variance labels are not member-name dispositions and do not count as a substitute for a name or as a suppressed member label.

## Read-only candidate evidence

Candidates were rendered in the isolated worktree at `b0ba79931dd9c7731255af7b09375bf4f47220fb`. Temporary View copies changed the existing Editorial View to `placement: both` and `backgroundDecoration.rows: alternate`; Candidate A declared `content: [title]`, and Candidate B declared `content: [title, finishDelta]`. Both used the unchanged Editorial Theme, Scheme, and Layout. Each was rendered through the CLI for HALCYON-1 and a project created with `chrona init`, producing Scene JSON, SVG, and PNG. Temporary files and images are under `/tmp/chrona-498-candidate-gXkw1E/` and are exploratory evidence, not committed acceptance artifacts.

| Render | Rows / bars | Full-width alternate bands | Visible member names | Suppressed member names | Separate variance labels | Visible-name row/end-start checks |
|---|---:|---:|---:|---:|---:|---|
| A — HALCYON-1 | 26 / 26 | 13; reach timeline end and guide all 26 rows by shared band edges | 23 | 3: `eps`, `detector`, `avionics` | 12 | all 23 names are within their own row and at their bar's start or end |
| B — HALCYON-1 | 26 / 26 | 13; reach timeline end and guide all 26 rows by shared band edges | 23 | 3: `structure`, `eps`, `detector` | 0 | all 23 combined strings are within their own row and at their bar's start or end |
| A — initialized starter | 3 / 3 | 2; reach timeline end and guide all 3 rows by shared band edges | 3 | 0 | 0 | all 3 names are within their own row and at their bar's start or end |
| B — initialized starter | 3 / 3 | 2; reach timeline end and guide all 3 rows by shared band edges | 3 | 0 | 0 | all 3 combined strings are within their own row and at their bar's start or end |

Scene and SVG counts matched: HALCYON A had 23 member-label IDs, 12 variance IDs, and 13 row-band IDs; HALCYON B had 23, 0, and 13 respectively. Starter A and B each had 3 member-label IDs, 0 variance IDs, and 2 row-band IDs. Every non-visible member name had the corresponding `W_LAYOUT_LABEL_SUPPRESSED:member-label:<row>:<object>` diagnostic, with no member-label primitive for that identity. Candidate A's separate variance identities were `mcs`, `optics`, `structure`, `eps`, `detector`, `avionics`, `payload-tvac`, `station`, `bus-test`, `comms-test`, `integration`, and `vibration`.

Candidate A retained short navy names and rendered the twelve known finish deltas as independent labels using the existing ahead, on-plan, and behind variance treatments. Candidate B appended values such as `+3d` to the navy names, producing longer labels that looked more crowded around bars and losing the independent variance color treatment. Both candidates met the structural name geometry checks. Candidate A is selected because it preserves the distinction between member identity and finish variance, and matches the already established title-only pattern used by the pinned `default-draft` View.

These renders reused the current Editorial Theme. Its row-band role resolves to gray `surfaceRaised` with opacity `1`; therefore the candidate stripes are heavier and cooler than the owner-selected faint warm tint. This comparison establishes row geometry and label behavior only. It does not select a tint or opacity, pass the candidate Theme through `starter-perceptibility`, or accept the default's final appearance.

## Corrected selected behavior

The bundled default continues to use a separate Editorial-derived View and Theme; the named `editorial` catalogue preset and `13-gallery-editorial` remain unchanged. The View declares:

- `visibility.labels.placement: both`, so the existing table name column remains while plot member labels are added;
- `visibility.labels.content: [title]`, so plot member labels contain names only;
- `visibility.labels.side: end` and `visibility.fallback.labels: [end, start, suppress]`;
- `backgroundDecoration.rows: alternate`.

With the existing Layout contract, omitting `finishDelta` from member-label content creates separate variance-label requests for combined items with known finish deltas. Layout keeps their existing variance role, candidate order, and overflow behavior. Do not encode deltas into member-name strings or add a local condition to suppress variance labels. A future change to variance visibility or placement requires its own design decision.

`View` owns declarative label content, placement preference, fallback, and row alternation. `Theme` owns the faint warm row-band paint token and opacity while preserving Editorial type, palette, and axis bindings. `Layout` owns member-name and variance-label measurement, geometry, candidates, overlap resolution, and suppression diagnostics. `Scene` carries the completed visible member and variance primitives plus row-band geometry; SVG and other adapters serialize them. No schema, Layout, Scene, adapter, CLI, or catalogue behavior change is selected.

## Literal issue acceptance criteria

The issue body and owner comment state these criteria verbatim:

1. “A bare `chrona render` of HALCYON-1 with no presentation flags gives every bar a row guide across the plot. It also names every bar at its end or start inside its own row, or reports the name suppressed.”
2. “The readable-defaults test renders the **bundled default** (no `--view/--theme/--layout/--scheme`), so a future repoint cannot bypass it. The pinned `default-draft` check may stay as an additional test.”
3. “The same holds for the `chrona init` starter.”
4. “The regenerated default for HALCYON-1 and the starter is committed as evidence. It is compared side by side with `13-gallery-editorial` in the acceptance review, and it keeps the same palette, type and axis.”

The correction changes none of these criteria. Separate variance labels are supplementary surface content; they do not satisfy a missing member-name disposition. The first three criteria require the actual bundled default and initialized starter, not only these explicit temporary View renders. The fourth still requires committed final default artifacts and a side-by-side comparison with `13-gallery-editorial`.

## Migration, diagnostics, and normative authority

Consumers of the bundled default will receive both plot names and separate finish-variance labels, as well as alternating row guidance. Suppressed names remain explicit Layout diagnostics and must not leave hidden text primitives. Consumers selecting the named `editorial` preset remain on its reference-faithful table-only, no-row-ground resources. No project migration or immutable Context rewrite is introduced.

No normative specification or ADR change is justified: the correction selects existing `View` content semantics and existing Layout behavior already used by the readable `default-draft` path. The architecture review amendment and implementation-plan amendment record how that composition is verified. If implementation finds a conflict with the normative contracts, pause and return to design before changing product code.
