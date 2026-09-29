# Architecture review — context-specific wallboard allocation (#504, #502)

Reviews the [design correction](../../design/issue-504-502-context-specific-wallboard-design-correction-2026-09-29.md), superseding the shared-resource recommendation in the [#530 amendment](../../planning/active/issue-504-502-lane-table-allocation-implementation-amendment-2026-09-29.md). The [implementation amendment](../../planning/active/issue-504-502-context-specific-wallboard-implementation-amendment-2026-09-29.md) is the next executable record.

## Decision and cross-architecture check

**Decision: use one standalone full Layout Profile for contexts 02/12; preserve shared `wallboard.yaml` and the 04/07/15 Context references.** This keeps the 300px allocation in Layout, where the composition resource owns sizing, and keeps lane naming/membership in View. It avoids both a View-content workaround and Scene/adapter changes. The existing #494 route-quality behavior remains authoritative: the correction must restore the intended route through declared geometry, not suppress or bypass a diagnostic.

The correction is consistent with Specification 33's complete-profile resource model, stable node IDs, immutable Context references, and the boundary that Layout owns composition while Scene carries completed geometry. It does not alter the profile grammar, schema, Theme, domain model, or compatibility promises. Although Specification 33 describes the `extends` format, current Render Context resolution and public materialization do not supply Layout bases. The correction correctly treats inheritance as an unimplemented end-to-end capability and defers it rather than assuming resolver-unit coverage is runtime support.

Whole-architecture responsibilities remain:

- View keeps the canonical lane labels, grouping and membership.
- Layout profile `wallboard-programme-board` supplies a 300px table floor for only its two referencing Contexts; Layout completes table/timeline geometry and route placement.
- Scene receives completed geometry and relation decisions; SVG/raster adapters serialize those results without layout policy.
- Context references pin immutable resource identity. The materializer regenerates derived closure identities from source bytes; no generated identity is hand-authored.

## Risk and disposition

The full profile copy can drift from shared wallboard as that resource evolves. For this narrow migration the drift is visible and testable; future shared evolution must explicitly update both resources or arrive with the separately reviewed Layout dependency-closure design. Do not silently rebase this migration onto `extends` until Context resolution and materialization support it. Preserve the unrelated contexts by comparing their committed outputs byte-for-byte.

No issue acceptance row is waived. The amendment retains literal #504/#502 acceptance and requires the normal focused tests, public Scene/SVG inspection, materializer batch, and artifact-diff check. This review approves the corrected design for implementation; it is not evidence that implementation or issue acceptance is complete.
