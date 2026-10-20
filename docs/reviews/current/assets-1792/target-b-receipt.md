# Issue 1792 — actual target-b regression

Input: [trial-9/big/big.chrona](https://github.com/tya5/chrona/blob/1ea19837198cce16d2d5f9a7493a73c1d77d1d67/trial-9/big/big.chrona),
SHA256 `764afc64c2e48981c52393a3f424d3ee9781a6edd0af7271d29a5a166bedadf4`.

Command: `.venv/bin/chrona render big.chrona --preset target-b --output target-b.svg --emit-scene target-b.scene.json`.
Own Python 3.13.7 venv, macOS 26.3.1 arm64. Source checkpoint
`4668b7173e8f41ab14de28fd0683729620592778` was committed during the render;
the final differences from loaded source were comments/types only, not behavior.
The process exit code and reliable total elapsed time were not retained;
[stdout](target-b-stdout.txt) reports `status: ok` and
[stderr](target-b-stderr.txt) contains exactly one early routing-cost warning.

| Comparison against pre-change measurement source `67313ef94` | Result |
| --- | --- |
| Prepared normal potential port pairs | 2,388, exceeding the measured 2,370 threshold |
| SVG | Byte-identical; SHA256 `a03bf4d252f6155006081ddc0e696b7ba7522aee5029eeb095e2d9688c7b8788` |
| Scene diagnostics | 80 → 81; no removals; only `W_LAYOUT_ROUTING_COST:surface=table-timeline;potentialPortPairs=2388` added |
| Every other Scene field | Equal, including primitives, routes, manifest and provenance |

Baseline Scene SHA256: `be4ec6a36f9b000bcdd020ea8033bca4ecd6906aad279b90ad4cc7ace0b0b594`.
New Scene SHA256: `478dd5970d4860b132519598522a47ea2198a98792107e267ab5150663c48801`.
This proves warning delivery without output-geometry changes, not render speed.
