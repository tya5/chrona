# Design Amendment — Legend-Only Paint Roles in Theme Admission (#478)

**Further correction:** [open-name overlap with axis typography](issue-478-open-role-family-overlap-correction-2026-09-27.md).

**Amends:** [role-admission rebase](issue-478-role-admission-rebase-correction-2026-09-27.md)
and the [axis-role amendment](issue-478-axis-typography-role-admission-amendment-2026-09-27.md).
**Adjacent authority:** [#427 legend dispatch amendment](issue-427-legend-swatches-design-amendment-2026-09-26.md).

The #427 contract deliberately permits an arbitrary Detail Profile legend
role. Known mark/line/decoration roles get their chart-matching swatch;
every other role gets a fixed-square `Rect` painted from that role. Theme
admission has no selected Detail Profile. Therefore a previously unseen role
with a **portable fixed-square paint** property is not inherently consumerless:
the explicit legend fallback is its producer/consumer rule. The original
#478 sentence “unknown roles fail” cannot override this later published
#427 contract without redesigning its authoring grammar.

Admit a bounded `legend-only paint` family for otherwise unregistered role
names. It permits only properties the fallback `Rect` swatch actually
serializes: `fill`, `stroke`, `strokeWidth`, `dash`, `opacity`, and the finite
gradient/shadow/stroke-finish declarations and fidelity that the Rect paint
pipeline supports. It does **not** admit typography, mark geometry,
`annotationContainer`, background/contrast policy, symbol, marker, icon or
axis-lane properties for an arbitrary name. A declaration used by a **known
non-legend consumer** must satisfy that consumer's narrower role contract;
the hypothetical legend fallback cannot legalize `variance-behind.strokeWidth`,
`annotation.strokeWidth`, or a Text/Icon shared-role effect. An otherwise
unknown role with unsupported properties still fails
`E_THEME_ROLE_PROPERTY_UNSUPPORTED` at its exact declaration pointer.

This preserves a concrete authored swatch behavior, not an unrestricted
wildcard. It also means a typo such as `plannned.fill` is syntactically and
semantically a possible legend-only role until a View/Detail Profile proves
it unused. Detecting unused declarations would require a separate
context-aware lint contract; #478 is a load-time **capability** gate, not an
unused-role linter. No Theme/View/Detail Profile schema or rendered output
changes. Tests must cover an arbitrary legend-only paint role, an invalid
geometry property on it, and a known text role whose stroke is still rejected.
