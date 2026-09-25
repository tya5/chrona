# Design Plan — Scene Perceptibility Gate (#446)

**Programme:** #454 D454-4, after P0 public-output corrections.  
**Entry state:** P0 source/evidence for #439/#443, #435, and #445 is published
through `5b14f13b`; its combined CI release evidence and acceptance review are
still pending.  This plan authorizes design/audit only, not #446 implementation.

## Purpose

The gate must inspect public serialized Scene facts without a rasterizer,
font metrics, renderer state, or a second layout algorithm.  It detects four
families: opaque later-paint text occlusion, slot escape, cross-domain text
intersection, and composited paint perceptibility.  It reports every finding
deterministically for every committed Scene and uses typed host relations,
not a numeric baseline or arbitrary primitive-ID allowlist, for intentional
hosted text overlap.

## Required audit

1. Read the exact current Scene schema/serialization model, paint ordering,
   `hostPlacementId`, slot overflow policy, `fitWarnings`, canvas paint, and
   draft render warning route.
2. Run a read-only prototype over regenerated P0 corpus evidence.  Record
   every finding by stable identity and classify it as a P0 regression, a
   typed intentional relationship, an explicitly declared visible overflow,
   or a #431 threshold-policy question.
3. Verify that #445's completed panel warnings distinguish permitted canvas
   growth from adjacent-slot escape; the gate must not relabel an explicitly
   completed Layout disposition as a defect.
4. Audit CI workflow boundaries so the checked corpus gate runs once in the
   existing conformance pipeline and does not duplicate full local suites.

## Design questions

| Question | Decision required before implementation |
| --- | --- |
| Finding identity | Versioned code plus deterministic Scene path/primitive IDs and measured facts; sorted independently of JSON input order where semantic order is absent. |
| Occlusion | Define opaque filled occluders, paint tie ordering, zero-area behavior, transformed bounds policy, overlap threshold, and the exact `hostPlacementId` exemption. |
| Slot escape | Define containment tolerance, optional/suppressed treatment, and how `visible-overflow`, `ellipsize`, `clip-optional`, and `fitWarnings` form an explicit disposition. |
| Text overlap | Define primitive eligibility, area tolerance, same-text exclusion, host relation exemption, and whether declared visible overflow remains reportable. |
| Paint perceptibility | Reuse a pure color-composition kernel; defer role classification/floors to #431 without creating a second contrast implementation. |
| Draft behavior | Run exactly the same evaluator after Scene construction and expose warnings without changing immutable Scene bytes or renderer output. |
| CI authority | Committed generated Scenes are the CI population; no baseline count suppression.  Invalid/missing Scene documents remain ordinary conformance failures. |

## Deliverables and sequencing

1. Publish a focused #446 design after the audit, then an architecture review
   against Layout/Scene/adapter ownership and #431’s policy boundary.
2. Publish an implementation plan that separately delivers pure evaluator and
   finding model, committed-corpus tool/CI gate, draft warnings, fixtures, and
   release review.
3. Start implementation only after the P0 acceptance review confirms no known
   P0 findings are encoded as exemptions.  If the audit finds a P0 defect,
   return to the owning P0 design rather than expanding #446 around it.
