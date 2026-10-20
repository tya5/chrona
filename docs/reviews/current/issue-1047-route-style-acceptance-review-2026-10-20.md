# Issue 1047 — route style acceptance

Curved slice source: `edb309c44`; integration: `0e926adc3` on ready
`e965de32769ec18a9ab8da6e80540bc427b6aac4`. Not whole-issue acceptance.
Design: Spec50, declared route style; final pre-code plan and architecture
review: [living Status](https://github.com/tya5/chrona/issues/1047#issuecomment-6282716395).

| Literal criterion | Status | Direct evidence / remaining work |
| --- | --- | --- |
| Both styles are declarable. Synthetic tests show no crossing of required labels and marks, or a counted, reported fallback to orthogonal. | not met | This slice implements `curved` only. `test_relation_style_surfaces.py` exercises actual table/Scene/SVG/PNG and network paths, safe mark/text clearance, orthogonal parity, terminal fallback and a required node that intersects only the curve causing counted clearance fallback. Geometry/completion/profile tests cover conservative ink, terminal runs and schema semantics. `metro` and release gates remain outstanding. |
| The Transit target slide (when one is reproduced) uses `metro` from YAML only. | deferred | Metro and reviewer-owned Transit reproduction/adoption remain outstanding. No authored example is changed to conceal a core side effect. |

Layout retains the selected skeleton, completes quadratic commands after
terminal completion, and preserves each surface's existing recovery and
crossing rules. Changed arcs have conservative stroke covers; no whole-host
exemption applies to them. Scene/adapters receive completed geometry, not a
style decision. Orthogonal omission/explicit selection preserves the existing
default pipeline and omits the default manifest property.
The shared vocabulary has one schema consumer; future metro widening can use
Spec56 §7's explicit single-consumer digest-update exception rather than a
duplicate grammar or unnecessary part version.

Local batches: profile/shared-schema205, geometry20, completion+geometry29,
integrated geometry/profile/network/rounding65, adjacent routing/engine126,
SVG/typeset/diagnostic92 passed. Schema equivalence: additive1/equal43;
L2/L3 pass with the same five pre-existing invalid fixtures. Its eleven new
style probes are additional observations, not weakened baseline expectations.
The documented prune proved and retired ten already-merged L1 allowances.

Actual render review: six surface tests pass; the different-row witness uses
opposite signed turns and two quadratic commands, not merely a U-shaped detour.
The coordinator inspected the actual PNG; curve and marks are distinct and
clear. PNG SHA256 `f67ebf5d048527ad8b67467489b4466bd7f2302d97f6c02cd6ec4b346db5e8d2`.
Reproduce with `pytest -q tests/unit/chrona/presentation/layout/test_relation_style_surfaces.py --basetemp=/tmp/chrona-1047-review`.
A nonuniform-pixel assertion prevents the earlier all-one-colour synthetic
Theme from passing as usable visual evidence. Genuine S geometry has its own
opposite-curvature test; terminal constraints still admit U/elbow/straight shapes
without inventing a detour. Final integration batch:117 passed.

Required: official CI snapshot review,
full exact-main three-OS release, metro, and Transit adoption. Keep issue1047
open until both literal rows and their required evidence are complete.
