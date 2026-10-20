# Issue 1792 row 1 — bounded workload measurements

Design/plan: [selected rule](https://github.com/tya5/chrona/issues/1792#issuecomment-6281002267).
Source: `67313ef94ed4a76afe75e01e99d66b7faa8b208c` (product-identical to
`cf11f07e4`; only three review files differ), clean checkout, its own Python
3.13.7 venv, macOS 26.3.1 arm64. Both CLI renders returned `status: ok`.

| Case | Primary input | Normal selections | Potential normal port pairs | Instrumented wall |
| --- | --- | ---: | ---: | ---: |
| trial9 target-b / best | `trial-9/big/big.chrona` at `1ea19837198cce16d2d5f9a7493a73c1d77d1d67`, SHA256 `764afc64c2e48981c52393a3f424d3ee9781a6edd0af7271d29a5a166bedadf4` | 234 | bounded 2,370–2,568 | 160.33 s |
| 1734 b240 / default first-fit | [trial-7/big/b240.yaml](https://github.com/tya5/chrona/blob/3f234372863763efdf5d22a140d44da11355f610/trial-7/big/b240.yaml), SHA256 `d4a2c834a3cf1cb28adac139c5d887806f6bd88d0465ffd85adec9a2694dd97d` | 336 per pass | 3,330 baseline; 3,321 label-recovery pass | 58.89 s |

The target profile records 267 best selections and 2,865 potential pairs,
including 33 contingent retry selections. Its histogram is 149×9, 82×12 and
36×15. Subtracting at most 15 per retry proves the 2,370 normal lower bound;
it does not count actual evaluated searches. First-fit can stop early; best,
blockers, hints, budgets and retries change actual cost. No seconds prediction
or comparison of instrumented timings to the uninstrumented 98 s is claimed.

`target-b-profile.json` was produced with probe SHA256 `488a3ae6…f92c6b1`.
That first probe also counted nested callbacks into its **first-fit bucket**;
exclude that bucket entirely. Its best route-call inputs are the reported
primary counts. The preserved `profile_route_candidates.py` is the corrected
probe (`75ec1e9a…bd4093f`) used for `b240-profile.json`; no original-script
identity or bit-reproduction claim is made for the first profile.

Only these two measured cases ran. Raw profiles retain timing and identity
evidence; rendered Scenes are not duplicated here. No product file was changed
by the probe, and the measurements did not change routing inputs or policies.

The post-change actual CLI regression is recorded in
[target-b-receipt.md](target-b-receipt.md), with its raw JSON stdout and stderr.
