# Architecture Review — L1 Project Revision and Context Font Root (#467, #494)

**Reviews:** [L1 revision and Context-root correction](../../design/issue-467-494-l1-current-project-revision-design-correction-2026-09-27.md). **Amends:** [L0 gate design amendment](../../design/issue-467-494-l0-gate-design-amendment-2026-09-27.md). **Plan:** [L1 implementation-plan amendment](../../planning/active/issue-467-494-l1-current-project-revision-implementation-plan-amendment-2026-09-27.md). **Review base:** published `main` `c06daa954b5a240e21343fc0705a4d4aaf7095eb`.

## Review decision

The selected fix is a one-line responsibility correction in `render_review`: default `asset_root` must use the Render Context's own immutable identity revision (`render_closure.context.identity.revision`), which matches the token under which `copy_context_closure` stages Context-owned font metrics/assets. Do not change materializer staging to the Theme token. For the supplied Project-v2/Theme-v1 case, migrate only Project tokens and pin Project content identity in the 15 Contexts; keep Theme v1 unchanged.

There is also a preexisting normative conflict that blocks full L1 materializer acceptance: Specification 50 requires exact authored Context bytes to be copied and prohibits mutation of parsed font metadata, but the current materializer rewrites font locators and serializes the altered Context. This conflict is outside the asset-root fix. L1 may proceed with scheduler-only preparation, but public materialization/generated evidence cannot be accepted or published as a complete L1 slice until the materializer contract is reconciled through a separate reviewed correction. This review does not claim Spec 50 compliance.

## Source and baseline findings

- `copy_context_closure` derives the returned Context reference token from the Project revision and places font assets in that snapshot directory.
- `render_review` currently selects `asset_root` from `render_closure.context.theme.revision_token`. This causes the failure for divergent Project/Theme tokens.
- Render Context owns `environment.fontMetrics`; selecting assets by Context identity is consistent with that ownership and with the current staging location.
- `_copy_reference` checks an optional `contentIdentity` against local bytes. Render Context v0.16 allows this field, so a Project digest pin needs no schema change.
- The current HALCYON corpus contains only `project.yaml`; local materialization reads that current path and does not fetch historical Project bytes by token. Updating it replaces prior working-tree bytes. Historical v1 remains available through prior Git/captures, not as a parallel current-corpus resource.

## Whole-architecture consistency

| Contract | Review finding |
|---|---|
| Specification 15 §§2, 6, 9 | Preserved by unique v2 Project token plus exact content digest; source history limits are stated accurately. |
| Specification 40 §2 | Asset-root correction aligns materializer staging and renderer lookup at Context identity. No materializer staging change. |
| Specification 50 | Existing implementation violates the requirement to copy authored Context bytes unchanged and not mutate parsed font metadata. This is an explicit blocker to L1 materializer/evidence acceptance, not an approved exception. |
| Render Context v0.16 | Optional Project `contentIdentity` is accepted and verified; no schema change. Theme references remain byte-for-byte unchanged. |
| Project/Schedule (Specs 04–05) | Only current Project `avionics-bustest` lag changes 2wd to 4wd; dates are scheduler-derived. |
| Context, Theme, Layout, Scene (Specs 06–08, 43, 50) | Context owns font metric configuration/root identity; Theme remains font selection. Layout measures only after metrics resolve; Scene carries completed geometry. No adapter acquires layout or font-resolution responsibility. |
| Frozen baseline, Actual, #498 I2 | Baseline and Actual remain unchanged. #498 I2 artifacts remain historical and are not rewritten or relabeled. |
| #467/#494 | No acceptance change. Lane/route results remain at L3; L1 cannot claim them. |

## Compatibility and focused verification

The required regression uses divergent revisions: Project/Context identity `project-v2`, Theme `theme-v1`. It must assert materializer font assets remain staged at Project-v2, default `render_review` root resolves Project-v2, and a public render succeeds with the pinned assets. Same-token behavior should remain byte-identical. Test the optional Project `contentIdentity` positive and mismatch paths. This is a narrow root-selection test; it does not establish Spec 50 exact-byte compliance.

The Spec 50 blocker must be resolved before L1 public materializer acceptance. Specifically, the implementation currently parses the authored Context, rewrites font locators from `package` to `context`, YAML-serializes the modified object, and returns a digest for those changed bytes. Specification 50 requires the authored Context copied byte-for-byte and a digest over those unchanged bytes; it prohibits rewriting font metadata. L1 cannot claim full acceptance under existing behavior. A separate design/review/plan correction must define a conformant representation for materialized assets without changing the authored Context before L1 publication proceeds. Do not fold that larger materializer redesign into the minimal `render_review` root selection without approval in the design record.

## Risks and disposition

- Do not advance Theme to compensate for the wrong root selector.
- Do not claim the current checkout preserves old Project-v1 bytes.
- Do not claim that the root fix resolves the Spec 50 violation.
- Do not publish generated L1 materializer artifacts as accepted while that violation remains unresolved.
- Reject Project or font digest mismatches; no token fallback is allowed.

**Review disposition:** the Context-root selection is coherent and suitable for focused implementation, but L1 materializer/evidence acceptance is blocked by the existing Spec 50 conflict pending a separately reviewed correction. No issue criterion or release gate is met by this review alone.
