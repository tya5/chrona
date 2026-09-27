# Implementation Review — M1 Generic Materializer Integrity (#467, #494)

**Reviewed commits:** `7e9cfd2ef0f203fad36b9dd1728da6f73a07e043` (overlay implementation) and `16ea8489e0b64512aff48acfee4e1a3bbfeed3a3` (CI gate alignment). **Base:** `d615bfb4f630f97fa4c4bb41b64b425a578d2ebb`. **Design authority:** [materializer context-integrity design plan](../../planning/active/issue-467-494-materializer-context-integrity-design-plan-2026-09-27.md), [context-integrity design correction](../../design/issue-467-494-l1-materializer-context-integrity-design-correction-2026-09-27.md), and [revision-overlay design correction](../../design/issue-467-494-materializer-revision-overlay-design-correction-2026-09-27.md). **Normative authority:** [Specification 40](../../specification/40-example-reproducibility-and-materialization.md), [Specification 50](../../specification/50-materializer-closure-integrity.md). **Implementation-plan authority:** [context-integrity implementation amendment](../../planning/active/issue-467-494-l1-materializer-context-integrity-implementation-plan-amendment-2026-09-27.md) and [revision-overlay implementation amendment](../../planning/active/issue-467-494-materializer-revision-overlay-implementation-plan-amendment-2026-09-27.md). **Review date:** 2026-09-27.

## Scope and disposition

This review accepts only the generic M1 materializer-integrity implementation slice at the reviewed commits. It does not accept L1 Project/Context migration or any #467 lane or #494 route criterion. Both GitHub issues were open at review time.

The implementation preserves the authored Context byte stream, stages verified package/provider resources in an execution-only namespace disjoint from revision/address paths, and keeps local resources at their declared revision/address. Resolver plumbing receives the authored identity and fails closed on key miss, missing staged bytes, changed bytes, or identity mismatch. No Context schema or canonical-reference migration is introduced.

## Evidence

### Focused checks

The supplied M1 verification results are:

| Check | Result |
|---|---:|
| Materializer integration suite | 37/37 passed |
| Font, renderer, and closure focused suites (five suites) | 46/46 passed |
| Full public materializer `--check` corpus | 28/28 passed |

The source diff includes direct checks for byte-identical copied Contexts, unchanged parsed mappings and authored icon references, package icon staging outside canonical revision paths, local reference revision/address copies, full-key isolation across provider/revision, and mutation/missing/stale-identity failures. These checks support M1's closure-integrity contract; they do not demonstrate lane layout or route acceptance.

### CI and public artifact inventory

- **Initial CI and correction:** [run 36297039531](https://github.com/tya5/chrona/actions/runs/36297039531) failed pytest on all three OSes in two tests that assumed pre-overlay staging: the package-backed `controller-z/material-icons` closure-input test used a raw local reader, and the snapshot-path fixture omitted `store.provider`. The generated diagnostic and declared-value inventories were also stale. `16ea8489` changed the first test to exercise the verified overlay without weakening its unused-input assertion, supplied an explicit local provider in the second, and regenerated both inventories. Conformance and newest-Python public reproduction were otherwise green in the initial run; wheel smoke was skipped downstream of pytest.
- **Release CI:** [run 36297505314](https://github.com/tya5/chrona/actions/runs/36297505314) passed all Ubuntu, macOS, and Windows conformance/full pytest/wheel-smoke jobs and the newest-Python public-materializer reproduction job on `16ea8489`.
- **Generated changes:** 28 Scene files changed; 0 SVG files changed. The Scene diff is provenance-only: each changed Scene updates the `render-context` provenance digest, with no geometry or painted primitive change reported in the diff inventory. No SVG output changed.
- **Raw Context digest example:** `halcyon-1/15-gallery-image-notes` now reports the SHA-256 of the exact authored YAML bytes, `sha256:5f5a167225ae1b00a003b3375b356208d2482217e4422c5105eaacc9e7cb7bd0`; the previous normalized/re-written Context digest was `sha256:d858f77f7943e967b6c470c646ed5a31703849f5dde2e315bae42560837eca4c`.
- **Package icon identity example:** `controller-z/contexts/material-icons.yaml` remains authored as provider `package`, identity `chrona.resources`, address `icons/material-symbols-outline-rounded-v2026-09-22.yaml`, revision token `v2026-09-22`, and content identity `sha256:c9550b8542dcc586757cee41e4d9ce90a3e12f2b8613056e4fabbc680b271b17`. Its generated Scene provenance reports that same icon-catalog revision and digest.

## Architecture and failure review

| Boundary | Finding |
|---|---|
| Materializer / use case | Owns provider resolution, exact-byte staging, identity verification, overlay construction, and temporary lifetime. Local resources remain in their declared revision/address path; provider-backed bytes use disjoint staging. |
| Revision Store / authored Context | Revision tokens remain opaque. Context bytes and parsed references are not rewritten, normalized, or backfilled. Staged content identity is checked before registration and checked again when read. |
| Font and icon resolver boundaries | Consume the original locator/reference through the overlay. The complete key preserves provider identity, address and resource revision where applicable, plus authored content identity where present. The materialized package icon fixture preserves `v2026-09-22` rather than substituting a local revision. |
| View / Theme / Context | Authored selection and identity fields remain their owners' data; the Context's emitted identity hashes its exact authored bytes. No schema migration is part of M1. |
| Layout / Scene / adapters | No provider, temporary-path, or materialization ownership is added. Layout receives resolved measurements/visual inputs; Scene contains completed facts; adapters serialize Scene. The generated Scene provenance-only update is consistent with this boundary. |

Missing providers/resources, unsafe paths, stale or mismatched identity, overlay misses, and staged-byte mutation fail closed through the existing reader/materializer/font/icon diagnostic families. There is no address-only, revision-only, latest-resource, or host-font fallback for required copied closure content. No persistent alias is created. The code and focused tests align with the Spec40 local/provider staging clarification and Spec50 authored-closure requirements.

## Literal issue acceptance

Every row below is deferred by this M1 review. The materializer is a prerequisite slice and supplies no user-visible lane/route evidence. Successor: [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md), especially its L3 gate; the issue-specific literal rows remain open until directly evidenced in the later lane/route acceptance review.

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27; issue open.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
|---:|---|---|---|---|
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | M1 changes materialization integrity only; no lane engine or lane-count/chain evidence. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | No lane-mode Scene/SVG evidence is produced by M1. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | M1 adds no lane assignment behavior or insertion-stability test. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | M1 does not implement or render lane labels/deltas. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | No View defaults, preset migration, or automatic-mode comparison is in this slice. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | M1's materializer corpus check is not lane-render evidence and does not migrate slides. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27; issue open.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
|---:|---|---|---|---|
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | M1 does not build lane routes or emit cause-specific route measurements. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | No lane-route implementation or 02/11/12 route test result is included in M1 evidence. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | M1 does not generate lane memberships or compare lane inventories. | [L0/L3 implementation amendment](../../planning/active/issue-467-494-l0-gate-implementation-plan-amendment-2026-09-27.md) |

## Release disposition

M1 implementation and release CI support the authored Context integrity and verified overlay behavior at the named commits. L1's Project revision migration and 15-context regeneration remain a separate planned slice; no L1 acceptance is claimed here. All nine literal #467/#494 acceptance rows are explicitly deferred with the planned L3 successor, so these issues remain open.
