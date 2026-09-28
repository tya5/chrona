# #466 C3 — balloon Scene kind architecture review

**Decision:** accept the [C3 correction](../../design/issue-466-c3-balloon-scene-kind-correction-2026-09-29.md). It resolves two introduced CI failures without changing the selected placement policy.

| Boundary | Consistency result |
| --- | --- |
| View / Project | No new intent, source identity or candidate; three note references remain unchanged. |
| Theme → Layout | The shared `annotationContainer` token already permits rectangle, balloon and image outlines. Layout owns the completed outline and route. |
| Layout → Scene | A closed outline is a painted `Symbol`; the separate routed connector is a `Path`. Role admission must accept `Rect`/`Symbol` for all annotation boxes and no other Scene kind. Route-length accumulation follows the existing float precision gate. |
| Scene → adapters / gates | Adapters serialize completed primitives; contrast/perceptibility already inspect `Rect`/`Symbol` grounds. C4's same-source note-box rule is unchanged. |

Specifications 07/08 are corrected with this review. This agrees with Specs 06/33/44/50 and the #465 container design; no schema migration or compatibility mode is needed. Verify the exact role-admission and float-accumulation tests, all 29 public materializers, then the 3-OS CI matrix before accepting C3.
