# Example Reproducibility and Context Materialization

**Status:** Design complete — Issue 38
**Depends on:** Render Context v0.5/v0.6 and Specification 38.

The PR/main evidence publication rule below is the approved #590 migration target. The I590-2 workflow transition implements the source-only PR snapshot and serialized main publication route; strict status-only branch protection is a separate I590-3 deployment gate and is not claimed until proven on a disposable protected branch.

## 1. Version policy

The public materializer accepts the live Render Context contract (currently
v0.17; Specification 13). Historical v0.5/v0.6 descriptions are not additional
runtime compatibility contracts. Deck authoring does not add an immutable
Context version or weaken reference validation.

## 2. Immutable closure materialization

Materialization is a test/example adapter, not a new runtime authority. For locally stored references, it copies each pinned resource into the directory named by that reference's own revision token and address. For package or other provider-backed resources that cannot be represented by that local revision store, it may stage verified bytes in a transient, disjoint execution-overlay namespace keyed by the full authored reference or asset-locator identity. That physical staging choice does not change the logical reference: provider identity, address, opaque revision token, and authored content identity remain intact, and the staged bytes must be exactly those resolved through that reference. In either case, materialization never replaces a declared revision with a primary revision, copies an embedded schedule payload, or resolves a latest resource. For v0.6 `inputs.snapshot`, it copies both the snapshot-ref resource and its nested Project reference, each at their declared revisions.

## 3. Context identities and expected SVG

Example Context files are derived immutable closure manifests. Any change to a referenced byte sequence requires updating its content identity in the same source change. Expected SVG and Scene bytes are regenerated through the public CLI, never hand edited. Source PRs carry the immutable closure and a CI-generated output preview, but do not commit the expected bytes; one serialized post-merge operation publishes those bytes on `main`. The acceptance test validates every top-level and input reference, including colorScheme, against the PR's freshly materialized snapshot or the synchronized `main` artifact as appropriate.

## 4. Verification and CI

The acceptance Context test selects the schema by Context version. Integration tests discover every output from the authored manifests, including outputs not yet tracked by Git, materialize each slide through `render-review`, compare its expected SVG and Scene byte-for-byte with the freshly generated PR snapshot or synchronized `main` artifacts, and prove mismatch detection. A removed manifest retires its previously generated SVG/Scene outputs in the same synchronized commit as the reports; it never authorizes deletion of unrelated or authored files. PR CI fails render/closure/quality errors and exposes source-caused output diffs, including retirements, without requiring stale committed evidence to match. A successful post-merge regeneration publishes the canonical derived bytes before exact-main release CI. A failed or pending regeneration blocks the next merge; a materialization failure remains a release failure.

## 5. Standalone adapter failure reporting

The standalone `tools/materialize_example.py` adapter leaves successful
materialization silent. On failure it emits one stdout JSON envelope
`{status, diagnostics}` using the shared application failure-report mapping
and exits with that report's code. Typed rejected/failed diagnostics retain
their codes, messages, source pointers and details; library materialization
calls still raise typed exceptions without printing. Artifact publication and
closure identity rules are unaffected.

## 6. Historical evidence

The three empty M27 documents are recovered only by verifying their exact historical non-empty blob/content identity. If no such verified content is accessible, they remain documented as unavailable rather than invented. The milestone ledger's current status must be regenerated only as a current operational record, never presented as historical review evidence.

## 7. Shared deck Context authoring (#415)

Status: selected design approved; implementation pending. This
section reserves the contract; it does not claim the current CLI supports it.

This is an authoring step before immutable materialization, not Context
inheritance in closure resolution. The existing manifest `context` and
slide-local `context` paths continue selecting explicit Context files unchanged.
They are not redefined as fragments.

A manifest may add `contextDefaults`, an inline partial Context **body**.
A slide may instead select `contextOverrides: {id: ..., body: ...}`; `id` is
required and names the resulting Context, not the slide or shared fragment.
`body` may be omitted when the defaults supply every required Context member.
Slide `context` and `contextOverrides` are mutually exclusive; a composed slide
requires declared `contextDefaults`. An explicit slide Context bypasses those
defaults. Absence of either slide selection retains the existing manifest
`context` fallback; no selection is inferred from neighbouring slides.

The composer starts with an empty body, applies `contextDefaults`, then the
selected slide body. Only these finite merge boundaries exist:

| Boundary | Rule |
| --- | --- |
| Context body | Merge by declared body member. |
| `inputs`, `environment` | Merge one level by declared property. |
| Resource/artifact references, `viewport`, `fontMetrics`, target descriptors, other objects and arrays | Replace as a whole; never merge individual reference fields or array items. |
| Explicit `null` | Remove that member; omission inherits it. The completed Context must still satisfy all required fields. |

All keys are closed against the live Context grammar. A dedicated authoring
schema reuses the existing Context property/reference definitions; it does not
copy Store, revision, digest, font or target grammars. Unknown/duplicate keys
and malformed values fail with a pointed authoring diagnostic before copying
resources or publishing artifacts. YAML mapping merges and cyclic aliases are
not an alternate override language. Missing required completed fields identify
the selected slide body and name the missing field. Invalid supplied values
identify their exact `/contextDefaults/...` or
`/slides/<index>/contextOverrides/...` origin, with the slide ID in the message.

One application-owned composer returns explicit Context bytes and their owned
staging address. It fixes `version`/`kind` to the live Context contract and uses
the slide's explicit Context ID. Its stable ordered YAML emission is ordinary
serialization, not source-format preservation. Composed Contexts use the
transient address `_deck-contexts/<manifest-id>/<slide-id>.yaml`, under the
ordinary primary-project revision and Store identity. The top-level reference
pins the digest of those exact expanded bytes; it must never claim the shared
fragment's address or identity. This address is not written into the author's
tree and cannot shadow an authored resource in the execution overlay.

Every surviving resource reference retains its exact declared Store, address,
revision and optional content identity; the existing copier/resolver verifies
it normally. Shared Store roots and Context font-asset bases remain relative
to the manifest root, as on the explicit materializer path. The composer does
not read neighbouring files, latest revisions or host defaults. There are no
recursive includes, implicit deck lookup or Layout/Scene/adapter merges.

Existing deck consumers must use that same selected explicit source, including
example initialization, derived Scene provenance checks, corpus/presentation
coverage and design-purity inspection. They must not assume that every slide
has an authored Context file, skip composed slides, or implement another merge.
Inspection can consume the composed bytes without publishing a temporary file.
Initialization retains its unavailable-provider filtering and never deletes an
authored file merely because a composed source has a virtual address. A manifest
ID is required for composition's owned address; explicit-only manifests that
previously omitted an ID remain valid.

`chrona materialize`, its library use case and the standalone tool reuse this
one composer. `render-review` still consumes only explicit immutable Context
references. A future authoring entry point must compose before calling that
immutable boundary, not add a second merge implementation.

Synthetic equivalent explicit/composed fixtures compare exact Context/SVG/Scene
bytes. Migration of existing authoring files may change Context provenance
because serialization changes: count those Scene-only differences explicitly;
SVG, geometry, paint and diagnostics must remain unchanged. Do not add a YAML
CST layer merely to freeze old Context hashes. Reviewer-owned HALCYON migration
and its same-cohort line/output table are required before issue415 closes.

## Boundary review

- Context owns immutable references; local resources are copied into their declared revision namespaces, while provider-backed resources may be exposed through a transient identity-keyed overlay without rewriting those references.
- CLI and closure validate/consume Contexts; they do not generate example authority.
- Examples own manifests and expected artifacts.
- CI owns reproducibility enforcement.
- No legacy Settings/Theme contract, mutable fallback, or project-specific branch is introduced.
