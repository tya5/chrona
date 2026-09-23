# #332 Opacity Contract Design Correction

## Trigger

During P332-2 projection preparation, the implementation inventory established
that current Theme v0.3 resources deliberately bind opacity only for roles that
are not opaque (group bands and calendar closure). Requiring a named `1.0`
token for every other role would make every existing and future Theme repeat
policy-free boilerplate without improving the Scene/adapter boundary.

## Correction

`opacity` is optional in the Theme role contract. Its absence means the closed
semantic value `1.0` **only in `ScenePaintResolver`**. The resolver writes that
value into every completed `ScenePaint`; no primitive remains unspecified and
no adapter chooses a default. A present opacity token still must be finite in
`[0,1]`.

This preserves the #315-A rule: adapter behavior is not a policy authority.
Stroke width and dash remain different: their absence is valid only when the
selected family has no stroke, and never gives a stroked primitive a fallback.

## Whole-architecture review

| Boundary | Result |
| --- | --- |
| Theme | Declares non-opaque opacity intentionally; does not repeat opaque tokens. |
| Scene resolver | Solely completes absent opacity to `1.0`. |
| Scene primitive | Always carries explicit completed opacity. |
| Renderer | Serializes supplied values and never infers one. |
| Layout / View | Remain outside the paint decision. |

The correction is narrower and more structured than forcing all Theme documents
to declare an equivalent token. It does not weaken failures for an invalid
declared token, stroke width, dash, fill, or stroke channel.
