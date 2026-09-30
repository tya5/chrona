# Architecture Review — Knobs for Hard-Coded Label Behaviour (#573)

Reviews [the design](../../design/issue-573-label-behaviour-knobs-design-2026-09-30.md) against AGENTS.md layer
boundaries and Spec 56 §3.2, on main `22ea2c1c`. Mechanics: [implementation plan](../../planning/active/issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md).

Verdict: the design is sound in layer and schema terms, with three amendments (A1-A3) the design text lacks and one
claim (decision 3 alongside byte identity) that cannot both hold. Not a rubber stamp; the amendments change behavior of the design as written.

## Checks that pass

- **Layer.** The end-gap bound and search band are arrangement policy relative to type size, decided during Layout
  placement. Theme carries appearance tokens; View carries author intent per view. The issue offers "Theme or Layout";
  Layout is right because `search` is already coupled to Layout's `rowDistribution`, and the bound is a placement rule, not an
  appearance. Nothing reaches Scene or adapters; the call site is the only consumer.
- **Schema.** `memberNames` is an optional object inserted under the existing `reviewSurface.properties`, itself
  `additionalProperties: false` and not in any `required` list change. That is exactly the additive optional case in Spec 56
  §3.2: no version bump, omission preserves prior behavior. The schema `default: 2` annotation (if written) must not be
  treated as the runtime value; the consumer supplies and tests it. The predecessor/successor conformance comparison applies
  only to new version pairs, so it is not triggered.
- **Derived profiles.** `profile.py` deep-copies the derived profile's own `reviewSurface`, and `overrides` reach only nodes
  under `root`, so `memberNames` follows the declaring profile with no new mechanism.

## Findings

**F1 / A1. A second two-em constant defeats the knob.** The same call site builds `MemberNameAssociation(..., 2 * float(font_size))`,
the nearest-perimeter distance from the completed Text to its own mark (Spec 50, "two-em ... nearest-perimeter gap"). On the
end side that distance is essentially the end gap. With only `maxEndGapEm` wired, a value above 2 is silently inert (the
association rejects the candidate first) and only values below 2 work. Amendment: the same value bounds both, so `reach =
maxEndGapEm * font_size (+ slip, A2)` replaces both `2 * font_size` occurrences. Consequence: the knob also widens or narrows
the association bound on the other sides. The name `maxEndGapEm` is then narrower than its effect; it is kept because the
design and issue name it, and Spec 50 must say what it bounds. The lead may prefer a separate knob or a renamed one; that is a
public-name decision and is flagged, not settled here.

**F2 / A2. Decision 3 (measure from the last own drawn mark) contradicts byte identity and is deferred.** The issue row and the
slice instruction require the default to keep today's output byte-identical. Decision 3 deliberately changes labels of slipped
actuals. Measured on main `e7c09a14` with a prototype (bound and association distance extended by the amount the item's rightmost own
mark passes its host): five public slides change (`aster-ssd/overview`, `halcyon-1/gallery-dark`,
`halcyon-1/gallery-editorial-lanes`, `halcyon-1/gallery-mono`, `halcyon-1/mission-brief`); in `aster-ssd/overview` a previously
suppressed `ftl` name is now emitted. Without the extension the same knob code changes zero slides. Decision: I573-1 ships the knobs
without the slip extension, so the default is byte-identical; decision 3 is separable (it needs `own_mark_right` on `LabelRequest` and an
extension term in `_member_reach`) and requires an explicit owner call, because it changes public output and the acceptance wording.
Byte identity is evidence of no change only, never of label quality.

**F3 / A3. Non-lane `full-band` and lane `side-band` under `fill` have no production evidence.** Today `full_band` is true only
for lane rows under `fill`; the block search assumes a lane row's stagger limit (`maximum_stagger`, set only for lane rows).
`search: full-band` on an automatic row runs the same contact search with no stagger cap, so it may move a label by more than one
step within the row band. That is a legitimate consequence of a general knob, but it is new behavior reachable only by opting in
and must be tested (automatic row, and lane row under `pack`) and documented in Spec 50 as not capped. `side-band` on a `fill`
lane row is the lane-and-pack path applied to a taller row; tests pin it.

**F4. Sharp edge: optional fields are not inherited.** A derived profile copies its own `reviewSurface` whole, so a base's
`memberNames` is dropped when the derived profile omits it (required siblings must be redeclared anyway, an optional one is
dropped silently). This is consistent with today's copy and is kept, but Spec 50/33 text and a test state it: a derived profile
declares `memberNames` itself.

**F5. Value range.** `maxEndGapEm` is `0..100` (the routing knobs use the same style of cap). `0` disables the `end` side
entirely (the existing `maximum_side_gap < gap` guard skips it) and is documented, not rejected. `place_member_name` already
rejects non-finite and negative values; the schema is the first gate, the function stays the last.

**F6. Manifest carriage.** `LayoutManifest` serializes `reviewSurface` (`rowDistribution`, `backgroundExtents`) into manifest
bytes, and the call site reads `layout_manifest.row_distribution`. `memberNames` must reach the call site the same way, and be
serialized only when declared, otherwise every manifest's bytes change and the default is not byte-identical. The profile
content hash already changes only for profiles that declare the knob.

**F7. Stale record.** The issue cites `surface_composer.py:2114/2177` and two call sites; main has one call site in
`surface_member_labels.py` and non-lane rows use `place_label`, not `place_member_name`. The design's link to a design plan
points at a file that does not exist; this plan and review are the only issue-573 records besides the design, and the design's
first line should point to the implementation plan instead (fixed in this docs PR).

## Not reviewed / open

- Whether `maxEndGapEm` should be split into an end-gap knob and an association-reach knob (F1).
- Scene-level acceptance of association after decision 3 is checked by the existing tests, not by a new Scene check.

## Addendum (2026-10-01, #679): decision 3 is taken; A2 is superseded

A2 deferred decision 3 because it contradicted the byte-identity acceptance row of #573. That was a scheduling call, not a
verdict on the rule. #679 records the case A2 left open, and #575 changes how a behaviour change is judged: byte identity
proves only that a change changed nothing; a behaviour change is reviewed against the general rule (synthetic tests) and the
approved targets (PR #461, the HALCYON target mock). The current corpus output is not an oracle.

**Why the last own mark is the right general rule.** A member name is associated with its item, and an item is drawn as up to
two marks in one row (planned or baseline, and actual). The reach exists so that a name stays attached to what it names and does
not become detached text. Measuring it from the planned mark alone gives a bound that depends on how far the actual slipped:
past 2 em of slip no end position is legal, so the name falls to the visible-overflow fallback that the association bound cannot
waive, and it is drawn on its own actual mark with `W_LAYOUT_LABEL_OVERFLOW` (measured for `attached-milestones` with the
original data: label 688.4-905.4 px against actual mark 720.7-726.7 px in `mission-light`, a 3.7 px start after the plan; the same
in all seven presets). The rule that a name is legal exactly when it is within reach of a mark of the item, and clear of them, is
independent of slip, so it is the rule a reader can state; the planned-only bound is an accident of which mark was the host.
No knob can substitute: `maxEndGapEm` 4 or 6 and `search: full-band` leave the label unmoved, because the failing candidate is
the end gap from the planned mark.

**What it means for `maxEndGapEm`'s name.** After the change the value is the reach from the item's last own mark on the end
side, and the nearest-perimeter distance to the nearest own mark elsewhere (F1 already made it bound both). "End gap" remains
accurate for what the name is most often used for (the gap between the end of the last mark and the name), and the schema, Spec
50, the design and the corpus use it; a rename is a public-name change with a schema migration and is not required for
correctness. I keep the name and record it as an open owner decision, not a settled one.

**What the deferred prototype changed.** The prototype extended both the end gap and the association distance by the amount
the item's rightmost own mark passes its host, and measured five changed public slides: `aster-ssd/overview` (a suppressed `ftl`
name is emitted), `halcyon-1/gallery-dark`, `gallery-editorial-lanes`, `gallery-mono`, `mission-brief`. Its per-primitive
explanation was not recorded, which is why deciding then was impossible. The extension also loosened above/below names, since
the association distance grew for every side. This slice does not repeat that: it measures the end gap
from the last own mark for the end side only, and the association from the nearest own mark, so a slip does not widen the reach
of a name that is placed above or below its item.

**What the evidence will be.** Regenerate corpus and public derived evidence locally on the code branch (nothing derived is
committed). For every changed slide: list the changed primitive classes and diff Scene primitives by id (member-label
bounds/rung/host, suppression, diagnostics), then explain each against the rule and against the PR #461 targets and the HALCYON
target mock. Expected classes: a member name that was placed at the planned-only bound now sits at its last own mark, a name
suppressed for lack of a legal position now emitted, and a `W_LAYOUT_LABEL_OVERFLOW` on a slipped item disappearing. Anything
else (a name moving with no slip, a mark, table or route change) is unexplained and stops the slice. The current look is not
kept for its own sake; a change that reads worse than the target is reported, not merged.

**Residual risks accepted, stated.** (1) The host reported for a name may now be the actual mark, which changes
`hostPlacementId` and the Scene acceptance pairing, both still exact. (2) `missing-actual` is not an own mark for reach. (3) The
start side is not measured from the first own mark; the case is symmetric (an actual earlier than the plan) and is not observed;
if the evidence shows a start-side overlap it is a separate slice.
