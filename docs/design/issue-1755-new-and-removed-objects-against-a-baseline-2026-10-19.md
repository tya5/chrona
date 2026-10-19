# Design note: objects added or removed since the baseline (#1755)

Status: proposed, for owner acceptance before code. Refs #1755.

## Root cause

`build_review_projection` (`src/chrona/presentation/model/projection.py`, forecast
branch) raises `E_FORECAST_BASELINE_UNAVAILABLE` when a displayed item has no
placement in the supplied Snapshot. A task added after the baseline therefore
fails the whole render, with `sourceRef` `/` and no hint. Separately, ghosts are
composed only per *selected current* item (`_compose_rows`), so a Snapshot object
with no current counterpart never produces a row, a ghost or a diagnostic. The
code is also absent from `skills/chrona/references/diagnostics.md`.

## Why a note first

The fix needs public vocabulary that does not exist today: a visible "new" /
"removed" marker text, and (for hidden ghosts) a diagnostic code. Both appear on
public output and in the diagnostics inventory, so they are proposed here.
Everything else is code and Spec 06 text.

## Proposed rule (matches the issue)

1. NEW: a selected item with no Snapshot counterpart draws normally. In forecast
   mode the forecast comparison fact carries no baseline distance
   (`ForecastComparisonFact.finish_delta` becomes `int | None`); the delta cell
   and variance paint are empty (no ahead/behind semantic), and the cell shows
   the marker. The forecast placement itself is still required: a missing
   *forecast* placement remains `E_FORECAST_BASELINE_UNAVAILABLE`, now
   documented as a real failure (forecast has no schedule for a displayed item),
   with the message naming the cause and the fix.
2. REMOVED: a Snapshot object with no current object, and which passes the
   View's selection (ids, types, object types), draws as a snapshot-only row in
   the document order position of its Snapshot hierarchy, as a ghost with the
   marker. If the View hides ghosts (`ghost-when-changed` counts a removed object
   as changed; `omitted` hides it), it is listed in one diagnostic instead.
   Explicit rows are unchanged: they name their objects.

## Recommended choices (need acceptance)

| Decision | Recommendation | Alternative |
| --- | --- | --- |
| New marker text | delta cell shows `new` (same code-owned family as `+4d*`; no new schema key) | wording key under `wording.*`, localizable |
| Removed marker | ghost label suffix `removed`, same mechanism | none |
| Hidden-ghost removed objects | new `I_BASELINE_OBJECT_REMOVED` (info, one record, ids and titles in the message, `sourceRef` the object pointer) added to the closed `ForecastInfo`/info set and to `docs/diagnostics/inventory.md` and `skills/chrona/references/diagnostics.md` | reuse no code; omit silently (rejected: the issue's complaint) |
| `E_FORECAST_BASELINE_UNAVAILABLE` | kept for a missing forecast placement only; message adds hint; listed in `diagnostics.md` | delete the code |
| Schemas | no View/Project/Layout schema change; no `version` bump (Spec 56 §3.2) | optional `comparison.removed: ghost|omit` knob, deferred |

## Side effects to measure in the implementation PR

- Forecast and ordinary Snapshot-compare renders in which an object exists on only
  one side: previously forecast refused, compare hid the removed object.
  Expected change in the 50 public slides: none or very few (published Snapshot
  pairs share object ids); the PR measures it with
  `tools/regenerate_public_examples.py --check` and reports counts, without editing
  `examples/**`.
- New diagnostic code count: 1 (`I_BASELINE_OBJECT_REMOVED`).
- Acceptance evidence: synthetic baseline plus one added and one removed task
  (forecast and baseline compare), and the trial-8 week-5 command with
  executive-light, target-b and marquee as PNGs under
  `docs/reviews/current/assets-1755/`.
