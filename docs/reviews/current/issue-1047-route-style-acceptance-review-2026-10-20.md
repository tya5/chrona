# Issue 1047 — route style acceptance

Metro source: `b8e737962`; curved PR1801 merged at
`56719e632326fe7a4eff56e87090ad33c1a5994d`.
Selected design and joint-budget correction were published before code resumed
at `ad6339174` / `f8eedb05e`; the final pre-code implementation plan and
whole-architecture review are in the
[living Status](https://github.com/tya5/chrona/issues/1047#issuecomment-6282716395).
Normative authority: Spec50, declared route style. Release gates remain pending.

| Literal criterion | Status | Direct evidence / remaining work |
| --- | --- | --- |
| Both styles are declarable. Synthetic tests show no crossing of required labels and marks, or a counted, reported fallback to orthogonal. | met locally; release pending | Profile schema/engine tests admit curved and metro. `test_relation_style_surfaces.py` renders a genuine opposite-curvature S; `test_metro_yaml_acceptance.py` renders normal YAML through actual table and nonstraight network pipelines (45° L plus Q, unchanged selected skeleton). `test_metro_route_safety.py` proves actual completion restores the selected path for diagonal-only and fillet-only required-node collisions; style receipts are typed/countable. Additional mark/text, radius and terminal controls are in `test_metro_style_surfaces.py`. |
| The Transit target slide (when one is reproduced) uses `metro` from YAML only. | deferred | Reviewer-owned reproduction/adoption remains outstanding. The [research target](../../research/presentation/transit-target-2026-09-26/README.md) explicitly identifies hand-drawn, not Chrona, output. This review accepts no reproduced Transit adoption; do not substitute the synthetic test slide for it. |

Architecture review: Layout owns selected-skeleton style completion, joint
chamfer/fillet/head allocation, conservative covers for changed Q **and L** ink,
and exact quadratic paint extrema. Both owners retain their existing stage,
crossing and critical/recovery rules. Scene/adapters only project/serialize
completed commands. Shared terminal extent uses the same extrema authority.
The shared vocabulary has one consumer; its deliberate enum widening and digest
update use Spec56 §7, with one explicit L1 expected delta.

Verification: final focused 236 tests passed (geometry, profile, shared completion,
both surfaces, normal YAML integration, bounds, terminals and default controls).
Ten Pillow deprecation warnings are from the existing terminal raster test, not
failures. Schema equivalence against projected curved base `446ea23fd` passed:
one declared enum widening, equal43, L2/L3 unchanged with five baseline invalid
fixtures. Repeat against current trusted ready main before final publication.
Focused reproduction:
`.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_metro*.py tests/integration/test_metro_yaml_acceptance.py`.

The coordinator inspected actual curved and metro PNGs. Metro YAML witness SHA256:
`5147053f265fa79ccab5dfa11971339992cd4e441b3d780b58510b9680cf2605`.
Curved PR CI39367673183 passed; official artifact12240560787
(`d38cb088c3e6e37b7cc45b75ef76d61bfae55438daebb878c9cb6b4c725607a3`)
has50SVG/50Scene unchanged and only expected inventory/coverage reports.
Metro official snapshot, exact-main full three-OS release and Transit disposition
are still required. Keep issue1047 open.
