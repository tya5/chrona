# Issue #590 — parallel-safe derived evidence work record

## Baseline and design plan

Public base: `6650a3715f137a65af6a6bf60316eb22e7795c80`. [Issue #590](https://github.com/tya5/chrona/issues/590) is open and the reviewer-maintained [board #454](https://github.com/tya5/chrona/issues/454) lists it first in P0, before #591 and #592. The only current workflow is `.github/workflows/conformance.yml`: PRs and `main` check committed generated examples and reports. `conformance/run_conformance.py` contains stale-report checks, and the public materializer integration test compares rendered bytes with committed outputs. `tools/regenerate_public_examples.py` writes or checks the manifest-listed Scene/SVG outputs. The repository has no `main` branch protection or ruleset and its default workflow permission is read-only. No post-merge regeneration job or merge queue is published. These are current-state facts; a working protected-branch/bot credential path and the complete derived-file inventory remain unverified.

### Literal issue acceptance

- [ ] Two PRs that each change a different Theme role can merge in either order without conflicts in derived files. Demonstrate this with two test PRs.
- [ ] A PR whose sources would produce different derived output shows that diff in CI and does not fail for "stale committed evidence".
- [ ] `main` is never left with stale derived files for longer than one post-merge job. A failing regeneration on main is visible and blocks the next merge.
- [ ] `AGENTS.md` describes the flow.

### Design questions and boundaries

1. Inventory generated Scene/SVG, diagnostics and gallery/corpus reports from their generator commands and Git paths. Separate generated evidence from authored design targets and from resource mirrors that must remain atomic with source changes. Define exact ordering, deterministic bytes and no-op behavior.
2. Design a PR preview that regenerates from untrusted PR sources with read-only permissions, displays source-caused changes (including rendered before/after evidence for behavior changes), and fails actual generation/quality errors without treating the old committed evidence as an oracle. Confirm all CI jobs that read derived artifacts use the same fresh snapshot.
3. Design one serialized post-merge operation that regenerates and publishes derived bytes on `main` without losing an intervening merge. Determine how its bot commit receives exact-main CI, since a `GITHUB_TOKEN` push does not itself trigger a new push workflow. Determine crash/retry and stale-base behavior.
4. Make “failure blocks the next merge” enforceable, not just documented: choose the minimum required check/ruleset or merge-queue configuration and verify bot publication is possible under it. A green check from an older base must not pass while regeneration is pending or failed. Repository administration and token/bypass settings are part of the design; do not enable an irreversible rule before a recovery path is tested.
5. Review consistency with Specs 40 and 22 (public reproducibility), #555's fast PR/full-main CI split, #575's visual-evidence principle, `AGENTS.md`'s exact review-bearing-main gate, and the requirement that full CI runs on the final derived commit. Preserve independent source ownership and serial `main` publication while allowing source PRs to coexist.

### Design slices and evidence

| Slice | Publishable result | Required evidence |
| --- | --- | --- |
| D1 inventory and contract | Exact derived-output manifest, PR/main state transitions, security and merge-gate choice, whole-architecture review, Specs 40/22 and AGENTS impact | Current generator/check coverage, GitHub settings capability, failure/retry and bot-CI proof. Publish before implementation planning. |
| P1 implementation plan | CI/scripts/tests/test-PR sequence and independent release units | File owners, safe migration of currently committed evidence, focused tests, artifacts, acceptance and rollback gate. |
| I1 PR preview | Source-only PRs regenerate in CI, report diff without stale-file failure | Synthetic changed-Theme fixture and byte/visual artifact; PR conformance and newest-Python reproduction. |
| I2 serialized main sync and merge gate | One post-merge regeneration/commit, exact final-main CI, enforced failure blocking | Success, no-op, failure, race/retry tests plus two different-Theme test PRs merged in both orders. |
| A1 acceptance | One literal review, issue closure, archive | Every criterion backed by PR/CI/branch-rule evidence; exact review-bearing `main` CI. |

Until D1 is published, do not change CI behavior or repository protection. #591 and #592 are separate P0 issues; #590 must not introduce their schema or Layout refactors.
