# Issue 1047 — route style acceptance

Metro [PR1803](https://github.com/tya5/chrona/pull/1803) source
`0e842ac5d84f4cb31bb387f6067f995fb3193d49`, merged at
`ddbd56fb1bc20b0e5e225db4a2f37f51773c114d` on trusted ready base
`98a8f3f83ea3c1ada559cb0617c0ca6a6dd74722`; curved PR1801 merged at
`56719e632326fe7a4eff56e87090ad33c1a5994d`.
Selected design and joint-budget correction were published before code resumed
at `ad6339174` / `f8eedb05e`; the final pre-code implementation plan and
whole-architecture review are in the
[living Status](https://github.com/tya5/chrona/issues/1047#issuecomment-6282716395).
Normative authority: Spec50, declared route style. The implementation release
passed. [Board454](https://github.com/tya5/chrona/issues/454) explicitly makes
target adoption reviewer-owned and not a dev closing condition.

| Literal criterion | Status | Direct evidence / remaining work |
| --- | --- | --- |
| Both styles are declarable. Synthetic tests show no crossing of required labels and marks, or a counted, reported fallback to orthogonal. | met; released | Profile schema/engine tests admit curved and metro. `test_relation_style_surfaces.py` renders a genuine opposite-curvature S; `test_metro_yaml_acceptance.py` renders normal YAML through actual table and nonstraight network pipelines (45° L plus Q, unchanged selected skeleton). `test_metro_route_safety.py` proves actual completion restores the selected path for diagonal-only and fillet-only required-node collisions; style receipts are typed/countable. Additional mark/text, radius and terminal controls are in `test_metro_style_surfaces.py`. Exact-main release below passed. |
| The Transit target slide (when one is reproduced) uses `metro` from YAML only. | deferred; reviewer-owned and non-gating per board454 | The [research target](../../research/presentation/transit-target-2026-09-26/README.md) explicitly identifies hand-drawn, not Chrona, output. No reproduced Transit adoption is claimed; synthetic fixtures do not substitute for it. The YAML-only requirement applies when the reviewer reproduces that target. |

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
failures. Schema equivalence against final ready main `98a8f3f83` passed:
one declared enum widening, equal43, L2/L3 unchanged with five baseline invalid
fixtures. Post-integration acceptance/schema-registry/parts controls:181 passed.
Focused reproduction:
`.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_metro*.py tests/integration/test_metro_yaml_acceptance.py`.

The coordinator inspected actual curved and metro PNGs. Metro YAML witness SHA256:
`5147053f265fa79ccab5dfa11971339992cd4e441b3d780b58510b9680cf2605`.
Curved PR CI39367673183 passed; official artifact12240560787
(`d38cb088c3e6e37b7cc45b75ef76d61bfae55438daebb878c9cb6b4c725607a3`)
has50SVG/50Scene unchanged and only expected inventory/coverage reports.
Metro [CI39371460608](https://github.com/tya5/chrona/actions/runs/39371460608)
passed all three pytest shards, conformance, newest-Python, MCP and readiness.
Corrected-head official artifact12241582735 (SHA256
`4aa9f867fc1a279ebe218f3bcb216207a87629069eab3b03b14b1cb9a27e644a`)
has50SVG/50Scene unchanged. Only coverage adds metro and inventory moves one
`E_LAYOUT_PATH_COMMAND_INVALID` site from terminal extent to shared path extrema
(same code/message). The coordinator independently checked hash, manifest and
the whole generated tree. Join tests use absolute1e-12/relative0 coordinate
tolerance across platform math libraries, exact topology and explicit45° checks.
Trusted review-containing main is
`9faf700f29e6d685410a5d492fc5daab81db0637` after successful derived-sync39372770884.
Its [native release39373223873](https://github.com/tya5/chrona/actions/runs/39373223873)
completed SUCCESS on Ubuntu, macOS and Windows (full pytest, conformance and
wheel), MCP floor and newest-Python reproduction. The exact updated-review-
containing main `37b3f5a988833b929509dfee3224e285bc2d51b2` also passed
[release39382911887](https://github.com/tya5/chrona/actions/runs/39382911887)
on all three OS, with conformance/wheel, MCP floor and newest-Python reproduction.
The board's explicit
reviewer-owned/non-gating disposition preserves the conditional target row;
it is not marked met. No unperformed target reproduction is claimed. The row
disposition and release were accepted in
[the closing review](https://github.com/tya5/chrona/issues/1047#issuecomment-6286050847).
