# M26 Cross-Boundary Closure Review — 2026-09-21

**Decision:** Reopens and closes the remaining M26 design before implementation resumes.

## Authority trace

| UC | Immutable inputs | Only permitted write | Product verb |
|---|---|---|---|
| UC-10 intake | command v0.2: Actual-set, batch, Project refs | target Actual Store CAS | `actual-intake` |
| UC-10 resolve | command v0.2: Actual-set, Project refs | target Actual Store CAS | `actual-resolve` |
| UC-11 check | command v0.2 plus Store config | none | `command-check` |
| UC-11 apply | command v0.2 plus Store config | one declared Actual CAS or baseline registry | `command-apply` |
| UC-12 capture | command v0.2: Project + registry refs | append-only baseline registry | `baseline-capture` |
| UC-12 compare | baseline + candidate refs | none | `baseline-compare` |

No verb derives a Store identity, address, revision, digest, baseline ID, output path,
or clock from a working tree, branch, or environment.

## Local adapter closure

`store-config/v0.1` is the only CLI Store lookup input. It maps an exact `(local,
identity)` pair to a root. Actual writes resolve immutable
`<root>/<token>/actuals/<id>.yaml` and compare the private
`actual-tips/<id>.json` pointer. Provisioning creates the first pointer out of band from
a verified immutable reference; a command never bootstraps it. Baselines are
create-once `snapshots/<id>.yaml` resources.

The local profile does not claim generic Project mutation. `command-apply` supports
only `applyActualIntakeBatch`, `resolveActualObservation`, and `captureSnapshot`;
`setTypedField` rejects as `E_AUTOMATION_OPERATION_UNSUPPORTED`.

## Dispatch, replay, and result

1. Parse/validate command v0.2 and verify every declared immutable reference.
2. Look up `(commandId, canonical request, target)` in the Store-owned replay ledger.
   An exact replay returns the stored accepted result with `replayed: true`; changed
   reuse is `E_COMMAND_ID_REUSE`.
3. `command-check` validates only. `command-apply` performs exactly one supported
   write then records the result. Rejected work performs no write.
4. `actual-intake`, `actual-resolve`, and `baseline-capture` are type-checked aliases
   of `command-apply`, so there is one Command Engine and result envelope.

Every product verb requires a create-once atomic `--result`: accepted is exit `0`, a
declared rejection is exit `2`, result publication failure is exit `3`, and syntax
failure before operation is exit `64`.

## Required evidence

| ID | Proof |
|---|---|
| C26-01 | check has no write and creates a canonical result |
| C26-02 | apply returns a new complete immutable Actual reference |
| C26-03 | exact replay returns stored result; changed ID reuse rejects |
| C26-04 | alias/type mismatch and unsupported type reject without write |
| C26-05 | missing Actual pointer rejects without bootstrap |
| C26-06 | capture is create-once and compare reads its result |
| C26-07 | all product verbs map 0/2/3 correctly |
| C26-08 | no raw `propose-set`, default Store, or current tip remains |

## Conclusion

The remaining endpoints, authority, persistence, replay, aliases, output behavior, and
unsupported-operation policy are now closed together. Any new verb, Store layout,
command type, or write capability reopens this review.
