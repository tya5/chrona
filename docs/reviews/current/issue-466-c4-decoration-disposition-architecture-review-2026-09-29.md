# #466 C4 — decoration disposition architecture review

**Decision:** accept the [disposition correction](../../design/issue-466-c4-decoration-disposition-correction-2026-09-29.md) before resuming C4 code. The initial materializer failure is a Theme-to-Scene capability conflation, not invalid note paint.

| Boundary | Reviewed rule |
| --- | --- |
| Theme / Spec 07 | `backgroundTreatment` is optional on decoration roles. If present, its finite treatment/order pair remains strictly validated; absence of the property means no background-treatment decision. |
| Semantic registry / Scene / Spec 08 | `DECORATION` activates contrast and corpus witness. Only an explicit `backgroundTreatment: none` emits an absence disposition; a painted note `Rect`/`Symbol` is a witness, not absent. |
| Layout / adapters | Completed note geometry and paint order are unchanged. Scene uses a typed Theme accessor; adapters serialize completed facts only. |

This aligns with Specs 06/07/08/33/44/50, #478 role admission, #465 image containers and C4's same-source box/text ground. No unresolved architecture conflict remains. Focused Theme-token and Scene-projection tests plus the public materializer/contrast batch are the release evidence.
