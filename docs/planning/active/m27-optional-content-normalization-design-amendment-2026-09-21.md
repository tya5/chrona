# M27 Optional Content Normalization Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R3B implementation is authorized.

The I27-R4 CLI currently normalizes table cells only. The old helper for optional
content accepts a deleted Settings contract and therefore cannot be reused. The v0.5
path instead derives `SurfaceContentInput` through one current-resource function:

* relations and Project semantic notes come from the selected Project/View visibility;
* View annotations become the normalized annotation family;
* legend/detail/summary data is included only when the corresponding current resolved
  profile resource is present in the Render Context; and
* every family remains absent when its source or Layout slot is absent.

The function accepts only the existing projection, Project, View, and resolved current
profile payloads. It has no Settings input, no profile/example branch, and no fallback
content. A present required family without its corresponding Layout source diagnoses
`E_PRESENTATION_PRIMITIVE_MISSING`; an absent optional source emits no primitive.
