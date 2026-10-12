# Annotation-policy design plan (#1343)

Baseline: published READY `b694b8589479bdf6bcf67ef9b1f3557067662f76`;
#1341 slice1 is merged. [Issue and accepted ownership split](https://github.com/tya5/chrona/issues/1343#issuecomment-6108475065)
are the source of scope; neither literal criterion is accepted yet.

| Literal acceptance | Required evidence |
| --- | --- |
| All five designs drop their per-id `annotations` list and still place HALCYON's three notes identically. | Test-local migration of all five; actual completed annotations and serialized SVG compared without identity/geometry normalization. |
| A project with different notes places them by kind. | Synthetic Project notes, point/span anchors, filtering, declaration-order permutations and explicit overrides. |

Do not edit `examples/**`; permanent adoption is reviewer-owned. Source audit
proves one purpose policy per design, but does not prove rendered acceptance.

Design order: close finite semantic bindings and selected-object membership;
close override/order/identity/failure rules; publish the Spec06/44 contract and
whole-architecture review; then finalize implementation slices.
Review Specs03/06/07/33/44/50/56 and #1341's immutable ingress overlay.
Project owns narrative and object anchors; View binds kind/facet/endpoint;
Layout profile offers purpose-keyed candidates, Layout completes geometry;
Scene/adapters do not select, measure or route. No project-ID selectors,
duplicated candidate language or paint-dependent semantic classification.
