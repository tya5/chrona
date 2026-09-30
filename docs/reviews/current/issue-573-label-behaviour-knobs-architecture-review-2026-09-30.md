# Architecture Review — Knobs for Hard-Coded Label Behaviour (#573)

Reviews [the design](../../design/issue-573-label-behaviour-knobs-design-2026-09-30.md) against AGENTS.md layer
boundaries and Spec 56 §3.2, on main `22ea2c1c`. Mechanics: [implementation plan](../../planning/active/issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md).

Verdict: the design is sound in layer and schema terms, with three amendments (A1-A3) the design text lacks and one
claim (byte identity) that holds only conditionally. Not a rubber stamp; the amendments change behavior of the design as written.

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

**F2 / A2. Byte identity is conditional, and decision 3 is a behavior change.** "Absent means byte-identical" holds for every
label whose item has no actual mark past its host. Decision 3 (measure from the item's last own drawn mark) deliberately
changes labels of slipped actuals, and the issue row says defaults keep today's output byte-identical. These two statements
conflict for those slides. The design accepts it, reviewed slide by slide; this review records that the acceptance row is
therefore met only for slides without slip, and that byte identity over the whole public corpus is not expected to be total.
Verification: `derived_evidence --check` and `regenerate_public_examples --check` are run on the slice; the set of changed
slides must be exactly the slipped-actual, end-placed labels and each is inspected. Any other diff means the implementation is
wrong or the design is, and the slice stops. Byte identity is evidence of no change only, never of label quality.
Mechanics: the host stays the anchor (planned mark for combined items); the bound is extended by `slip`, the amount the item's
rightmost own mark extends past the host's right edge. The association host is unchanged, so Scene-side `hostPlacementId`
pairing is unaffected.

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
