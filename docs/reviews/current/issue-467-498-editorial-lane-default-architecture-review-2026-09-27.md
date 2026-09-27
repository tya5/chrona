# Architecture Review — Lane Defaults and Editorial Reference (#467, #498)

**Reviews:** [design correction](../../design/issue-467-498-editorial-lane-default-design-correction-2026-09-27.md). **Base reviewed:** published `main` commit `a28793e2` (L1/L2 plus published staged L3a/L3b design records). **Owner decision:** all packaged preset Views use lanes; preserve the Editorial reference under a separate gallery name. **Related accepted evidence:** [#498 readability release review](issue-498-bundled-default-readability-acceptance-review-2026-09-27.md). **Status:** design consistency review; implementation and release acceptance remain pending.

## Decision reviewed

The current `library.yaml` has seven catalogue entries, and `presets/default.yaml` is a separate eighth packaged preset View. All eight preset selections resolve lane Views under the existing View v0.27 `rows.mode: lanes` contract. For the `editorial` catalogue entry, add a new lane View at `presets/bundles/editorial/view-lanes.yaml` with ID `chrona-preset-editorial-lanes`; keep the existing `view.yaml`/`chrona-preset-editorial` as the reference resource and change the catalogue member to the new path/ID. Keep corpus `views/editorial.yaml`, the complete `13-gallery-editorial` Context, and its generated Scene/SVG/PNG unchanged. Add byte-identical lane mirror `views/editorial-lanes.yaml` and the distinct `gallery-editorial-lanes` slide / `16-gallery-editorial-lanes` Context. Give the unchanged reference slide the human-facing gallery title `Editorial Reference`.

This preserves #467's packaged-preset acceptance and #498's readability goal while leaving the existing reference resources and outputs untouched. No old View revision must be resolved from Git because the old address is never changed. New lane output receives its own resource, Context, slide and artifacts. The old #498 Scene/SVG/PNG and review remain historical evidence of the accepted prior default resource version. New L3c evidence must prove readability on current default resources.

## Baseline and source checks

Read and compared:

- Issue #467 body and all later owner comments, including the exact six literal acceptance rows, the L3 handoff and latest L3 remeasurement. The old remote lane branch is explicitly unaccepted: 13 lanes, chain collision, and route work remains subject to current-base evidence.
- Issue #498 body, owner decision and acceptance comments. Its current accepted review records four met criteria on the previously shipped readable Editorial default, `chrona init` starter and unchanged reference slide.
- The active joint decision plan, existing #467 design, View v0.27 clarification, route/phase correction, L3b preflight correction and L3 publication amendment.
- Specifications 06, 07, 08, 24, 38, 40, 50, 55, 58 and 62; ADR-0029; the #466 shared-obstacle and route-priority correction; #425 Editorial reference; #470 catalogue integration; #429/#383 catalogue definition; #479/#486 resource versions and attached points; #480/#481/#487 layout contracts; and the #498 architecture, plan and acceptance records.
- `src/chrona/resources/presets/library.yaml`, all eight View members, `presets/default.yaml`, the starter resource provider, the HALCYON manifest and candidate Context files; `13-gallery-editorial` has `example-v1` on the View and no authored View `contentIdentity`.

The plan's phrase “eight packaged presets” is imprecise: `library.yaml` contains seven catalogue entries. The eighth View is the separate bundled-default selector. The correction uses that explicit 7+1 inventory. This is verified from the published resource file and must remain the implementation inventory. No issue body was modified by this design choice.

## Whole-architecture consistency

### Domain, View and Theme

No Project, schedule, Actual observation, dependency, or milestone attachment changes are authorized. View owns the selected items, grouping, ordering, lane-table summary, required title/delta intent and the `automatic` opt-out. It forbids item-subject table columns in lane mode under v0.27. Theme and Scheme continue to own the Editorial palette, typography, axis and faint warm guide treatment. The existing Editorial reference's ordinary resources remain frozen as the old reference rather than being repointed.

The new-View requirement is a producer/template policy, not an implicit schema default: v0.27 still requires an explicit row mode, preserving immutable resource meaning. The default new-View creator must emit `lanes`; authors can deliberately select `automatic`. The existing `default-draft` example is not itself the bundled default and cannot substitute for testing that creator or the bare CLI path.

### Layout, Scene, adapters

The L3b single immutable `SurfaceLanePlan` remains the only lane identity and allocation authority. The lane preflight closes after finite seed inline geometry, feeds the #480 shared text-aware row extent and #487 sizing path, includes #481 group bands, and consumes #486 attached-point semantics. Required names and selected deltas remain phase-one measured text and shared obstacles before semantic route completion; #466's route priority and cause accounting remain in force. A lane allocation never moves into a renderer or depends on palette/catalogue metadata.

Scene carries final lane rows, lane table values, names, deltas, row guides, marks, and routed or suppressed dependency outcomes. SVG/PNG/other adapters serialize completed Scene output. Neither Scene nor adapters infer the member associated with a lane label, re-add table facts, repair crossings, or change suppression. Automatic output stays unchanged for unchanged Views.

### Context, package, identity and examples

Each preset still resolves to ordinary versioned resources from the wheel-owned catalogue. Catalogue ID and gallery set metadata are not rendering policy. Default selection remains `chrona-default-draft`; the starter resolves through the same exact selector. Corpus package mirrors and Context resource references must be regenerated or repinned as ordinary resources, with hashes and manifest reachability checked. Existing immutable Contexts are not rewritten in place.

Specification 58's corpus/gallery distinction supports this identity migration. Existing package and corpus reference View bytes are SHA-256 `e8bcbbab4134a6b4f596cace618bde0c6b02484785bc07df8b225b9c506f0e8b`; current Context 13 hash is `ed7c2896e2787e1a10d281d9c8f76ecb4cd8c23dde244ab957ff8572961ce98d`. Keep those resources/Context and generated artifacts byte-identical. The catalogue points to the new resource `chrona-preset-editorial-lanes` at `view-lanes.yaml`; its corpus mirror uses `views/editorial-lanes.yaml`. Context and slide 16 have distinct IDs, and the materializer proves the package/corpus lane resource byte identity. Existing 13 hashes remain valid as current expectations.

### Compatibility and migration effects

The migration intentionally changes rendered row/table content for the eight named packaged defaults: per-item columns give way to lane/group summary cells, while names and selected deltas appear as required plot text. This may change viewport height, output bytes, and where facts are read. The design records this user-visible change instead of preserving legacy resource bytes as the default. The named `editorial` resource IDs remain stable but content changes in the next published resource revision; the public default alias stays the same while its effective View closure changes.

Existing custom immutable Views in automatic mode retain their current row composition. The unchanged `13-gallery-editorial` resolves the same existing local reference, and the new lane Context resolves a new local path/ID. The acceptance record for #498 is not overwritten; a successor test and review checks current default/starter and compares them with this reproducible Editorial Reference.

## Acceptance and visual evidence obligations

The design is consistent only if implementation evidence covers all literal #467 rows, including ≤12 lanes and chain identity, no suppressed lane name, determinism/insertion stability, visible deltas, default behavior and three committed slides. Current 02/11/12 route-cause and non-crossing gates remain from #494. All eight packaged Views require materialization in project-generic test fixtures, not only a single HALCYON slide.

For #498, the new default and initialized starter need bare CLI Scene, SVG, and PNG artifacts. Scene checks verify each selected title has a required lane label and matches its lane; rendered output inspection verifies row guides, title readability, Editorial palette/type/axis, and table lane-summary clarity. Compare both with `13-gallery-editorial` / `Editorial Reference`. Keep the accepted pre-migration evidence unchanged and make clear that it proves the old resource version; it cannot alone prove the post-migration default.

Generated public materializers, resource mirror identity, source-to-output hashes, and exact generated byte diffs are part of the L3c review. A Scene-only result is not proof of the #498 visible appearance. Full CI and public-materializer gates remain the release gate prescribed by the L3 plan.

## Risks and disposition

1. **Lane geometry is not yet an acceptance result.** The new public migration depends on accepted L3b measurements; do not expose `lanes` if the current 4wd data still exceeds twelve lanes, fails the named chain, or routes across required labels.
2. **Preset themes may not all express lane table and guide paint adequately.** Test all eight closures. Any new Theme role or schema requirement is a design change requiring a further architecture review and normative update before resource edits.
3. **#498 and #467 output requirements meet at required labels.** The lane view must show both title and selected delta without suppressing titles. The reviewer should check actual SVG/PNG crowding, including narrow/small starter output, rather than relying only on geometry assertions.
4. **Catalogue and corpus identities differ by design.** The catalogue's `editorial` member and new lane Context must use `chrona-preset-editorial-lanes`; the old Context must keep `chrona-preset-editorial`. Update hard-coded public preset evidence expectations and add a direct package/corpus hash-equality assertion for the lane files so these two intents cannot drift or be confused.
5. **New-View producer location needs exact inventory.** Before product changes, trace every code/template path that creates a new View. Add a direct creator test and ensure only its default changes; do not fake a schema default or rewrite the pinned `default-draft` example.

No change to the semantic model, output schema, identity law, package resolver, lane algorithm, failure policy or rendering layer ownership is accepted here. No ADR is warranted. Specification 38 and Specification 58 are the normative homes for row-mode defaults and gallery identity respectively.

## Review conclusion

The selected 7+1 migration and separate Editorial Reference gallery identity are architecturally coherent under the published contracts. This design correction and review authorize L3c implementation planning; they do not authorize activation before the L3b gates pass. L3c remains unaccepted until the implementation amendment is published and every literal criterion plus public materializer/CI evidence is recorded.
