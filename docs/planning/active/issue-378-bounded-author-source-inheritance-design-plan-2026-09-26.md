# Design Plan — Bounded Author-Source Inheritance (#378 I378-2)

**Status:** Active design plan.

## Purpose

Plan the fifth onboarding rung without adding generic YAML merging.  A derived
Theme or View must be resolved into an ordinary effective resource before
closure, Layout, Scene, or an adapter receives it.

## Evidence to inspect

1. The current Theme v0.11 and View v0.21 schemas, contract parsing, Draft
   preset ingress, immutable Context closure, and canonical identity producer.
2. Layout Profile's existing pinned-base implementation, solely as evidence
   for identity and cycle requirements; it is not an implementation to reuse.
3. Guided-workspace `binding.overrides`, to prove it remains operational
   governance rather than an author-source inheritance mechanism.
4. The five-line Theme acceptance need, current renderer-owned responsibilities,
   and public materializer closure/receipt representations.

## Decisions required before implementation

| Question | Required decision criterion |
| --- | --- |
| Base address | A typed local relative reference with exact content identity; no ambient file discovery or identifier-only lookup. |
| Resolution location | A presentation ingress resolver, before typed contracts and Layout; never Scene, adapter, or Theme consumer. |
| Theme override domain | Only named `body.values` entries and named `body.roles` entries, preserving the base document's closed structure and validating the resulting ordinary Theme. |
| View override domain | Audit every View field. Admit only fields whose replacement cannot mix selection, scheduling facts, or renderer policy; otherwise explicitly defer View inheritance rather than inventing a merge. |
| Identity and closure | Effective resource identity is canonical bytes of the validated resolved document; closure retains the derived source and pinned base evidence. |
| Failure model | Missing base, identity mismatch, kind/version mismatch, traversal, cycle, unknown override key, and invalid resolved document have stable ingress diagnostics. |
| Context boundary | Draft and immutable Context paths use the same resolver; materialization records only closed effective ordinary resources. |

## Deliverables

1. An English architecture design and independent whole-architecture review.
2. A separately published implementation plan with slices for contract/schema,
   ingress resolution, closure/identity, and acceptance evidence.
3. No code in this planning slice.  If the View audit does not establish a
   safe finite override surface, the implementation plan must exclude View
   inheritance and record its successor boundary explicitly.

## Review gates

- Confirm that no effective resource can silently depend on unpinned local
  state after closure.
- Confirm that the proposal neither extends `binding.overrides` nor exposes
  Layout/Scene/adapter mechanics through Theme or View.
- Confirm that a five-line derived Theme can be an ordinary editable source
  fixture, not a special renderer-side mode.
