# Implementation Plan Amendment — L1 Project Identity and Context Font Root (#467, #494)

**Amends:** [L0 gate implementation-plan amendment](issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md). **Design:** [L1 Project revision/Context-root correction](../../design/issue-467-494-l1-current-project-revision-design-correction-2026-09-27.md). **Architecture review:** [L1 review](../../reviews/current/issue-467-494-l1-current-project-revision-architecture-review-2026-09-27.md). **Base:** published `origin/main` `c06daa954b5a240e21343fc0705a4d4aaf7095eb`.

## Scope and publication boundary

The narrow implementation correction changes the default font asset root in `render_review` to the Render Context identity revision. Materializer staging remains under its emitted Context token, which is the Project token. L1 also corrects the current Project and pins its exact content identity in all 15 Contexts. It does not change Theme pins or bytes and does not move lane acceptance out of L3.

**Acceptance blocker:** Current `copy_context_closure` rewrites the authored Context's font locators to `provider: context` and serializes the modified YAML. Specification 50 requires the authored Context to be copied byte-for-byte and forbids mutation of parsed font metadata. Therefore L1 may complete scheduler-only preparation, but cannot publish or accept its public materializer/generated-evidence slice until a separate reviewed design correction resolves this normative conflict. This amendment does not authorize a Spec 50 exception or include the materializer redesign in the root-selection change.

## L1 scoped work

| Work | Owned files/resources | Focused verification and acceptance gate |
|---|---|---|
| Align font asset root | `src/chrona/usecases/render_review.py`: choose the default `asset_root` using `snapshot_directory(request.snapshot_root, render_closure.context.identity.revision)` or equivalent Context identity, rather than the Theme revision token. Do not change `src/chrona/usecases/materialize.py` font staging. | Add a divergent-token regression with Project/Context revision v2 and Theme revision v1. Assert materializer stages assets under the emitted Context token, default `render_review` resolves that same root, and render succeeds with the pinned assets. Verify equal-token behavior remains byte-identical. |
| Test Project digest enforcement | Focused coverage adjacent to materializer tests: set Project `contentIdentity` to the target SHA and exercise both valid bytes and a mismatch. | Valid digest passes; stale/mismatched Project bytes reject with the existing `E_CONTENT_IDENTITY` path. Do not claim this test establishes Spec 50 compliance. |
| Correct current Project resource | `examples/halcyon-1/project.yaml`: change only `avionics-bustest.lag` from 2wd to 4wd. Target SHA-256: `e196a21b0162e28d318f7e6512ada534cc1b6cdc35edb8fad6d84926bc4ca840`; reference it as `example-v2`. | Confirm only the approved lag changes and the resulting normalized bytes match the target digest. The current corpus has one `project.yaml`; updating it replaces previous bytes in the worktree. Do not claim a v1 Project copy exists in current corpus; historical v1 is in prior Git/captures. |
| Migrate current Context pins | All 15 `examples/halcyon-1/contexts/*.yaml`: set only `body.project.revision.token` to `example-v2` and add `body.project.contentIdentity` with the exact Project digest. Keep Theme references/bytes/tokens at v1 and all other references unchanged. | Count and enumerate all 15 Contexts. Validate schema; compare Theme and unrelated reference objects byte-for-byte/semantically unchanged; verify every Project token and digest agrees. |
| Preserve historical inputs | `examples/halcyon-1/actual.yaml`, frozen `snapshots/baseline-2027-06/`, and historical #498 I2 outputs. | Byte compare Actual and frozen baseline. Keep prior I2 captures and provenance untouched; new current evidence must be identified separately. |
| Public materializer and output batch | Re-materialize 15 Contexts and regenerate current schedule/Scene/SVG/PNG or other dependent artifacts only after the Spec 50 blocker is closed by its separate reviewed correction. | Verify exact content identities, root regression, full output inventory, and SVG/Scene inspection. Until blocker resolution, these results may be used for diagnosis but cannot be accepted or published as conformant L1 evidence. |

## Normative blocker assessment

Specification 50 §1 requires the authored Context file to be copied byte-for-byte and says the materializer must not serialize parsed YAML back to the copied path. It also says font metadata must not be mutated. Current `copy_context_closure` violates both requirements by rewriting font locators and serializing its modified in-memory Context. Specifications 38/40 do not authorize this exception: Spec 40 describes derived immutable closure manifests, while Spec 50 states the stricter current integrity contract. The L1 root-selection fix does not address that discrepancy.

Before L1 materializer acceptance or publication, a separate design correction, whole-architecture review, and implementation-plan amendment must decide how font assets can be made available under the Context root while preserving the exact authored Context bytes and satisfying the declared locator contract. Do not change Specification 50 silently and do not widen the current root-selection code change to include a speculative locator/model redesign. Until then, scheduler facts and candidate resource diffs can be prepared, but the complete L1 slice is blocked.

## L1 review record and continuation

Once unblocked, record base/result commits, focused commands, divergent token test, Project digest, all 15 migrated Context IDs, unchanged Theme/unrelated pins, baseline/Actual byte checks, complete artifact diff inventory, and rendered inspection. State that L1 makes no claim about lane acceptance. L3 remains the first valid lane/route acceptance measurement against the v2 Project and v1 Theme closure. #498 I2 remains historical.

## Literal issue acceptance criteria — unchanged

The following text is copied from the live issue bodies; this amendment neither narrows nor marks any row met.

### #467

1. “A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.”
2. “Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.”
3. “Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.”
4. “Deltas remain visible for packed items that have them.”
5. “New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.”
6. “At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.”

### #494

1. “On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause.”
2. “`test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label.”
3. “Lane count and lane membership on 02 are unchanged, or any change is attributed.”
