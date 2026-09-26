# Reproduction — Declared Treatment Visibility (#478)

This is evidence for [the published design plan](../../planning/active/issue-478-declared-treatment-visibility-design-plan-2026-09-26.md), not a selected contract. It was collected from published `main` before #478 product changes. Issue #479 separately owns preset-selected visual profiles.

## Three distinct phenomena

1. **Supported treatment, omitted by profile.** A copied `elevated-light` preset declares `decorative-optional` gradient and shadow on its group band. Rendering HALCYON-1 with the default `chrona-output/visual/v0.5-baseline` produces six group-band primitives with neither treatment. Rendering the same input with `chrona-output/visual/v0.7-svg` produces six with both; the SVG contains the shadow filter. Neither Scene reports an omission fact. This is the first acceptance defect.
2. **A mark can carry a shadow.** Adding complete shadow tokens and a `shadowColor` binding to the copied Theme's `planned` role yields no planned-mark shadow in the baseline Scene, but planned Rect/Symbol shadows and SVG filters under the rich profile. Thus issue #478's example that mark shadows are inherently ignored is too broad. The omission is profile-driven for these primitives. A role/property applicability rule must not reject `planned.shadow` merely because the baseline profile drops it.
3. **Suppression evidence exists but is not aggregated.** The HALCYON-1 render has `W_LAYOUT_LABEL_SUPPRESSED:member-label:structure:structure` in Scene diagnostics. Layout emits a fact for each suppressed placement; the CLI warning path does not print these Scene facts, and there is no count-bearing info diagnostic. The suppressed label does not become a Scene text primitive, as Specification 50 requires.

## Contract-path observations

- `scene/paint.py::_admit` returns `False` for a decorative-optional treatment absent from the chosen profile. Its caller replaces that treatment with `None` and returns only `ScenePaint`; it has no disposition output.
- `scene/v05_builder.py::_complete_surface_paint` resolves paint for emitted primitives and canvas. It does not inspect every Theme declaration. `color_scheme.resolve_theme` closes Scheme bindings into a resolved Theme, but has no role/property applicability gate.
- Profile capabilities live in `scene/visual_capabilities.py`; the baseline admits mark geometry but not gradient/shadow/stroke finish, while `v0.6-svg`, `v0.6-png`, `v0.7-svg`, and `v0.7-png` admit those rich treatments. The profile suggestion must match the target kind; baseline omission must not upgrade the render automatically.
- The SVG adapter uses completed paint for Rect, Text, Symbol, and Path, but its Icon branch projects closed icon paths rather than outer paint attributes. `text` is used by both Text and Icon in public Scenes. Consequently a role's applicability cannot be inferred only from its name or from a single primitive instance.
- Theme roles are not identical to Scene visual roles. Some roles are used for typography or semantic tokens, and some color bindings introduce roles absent from explicit `body.roles`. A validator needs the complete role-consumer registry and must check direct and Scheme-introduced bindings after inheritance/closure.
- Existing shipped resources contain apparent silent declarations, notably `baseline.stroke`/`strokeWidth` while no public Scene visual role is `baseline`, and `variance-behind.strokeWidth` while its public Scene primitives are Text. Before adding a strict gate, validate the full catalogue and migrate or explicitly justify each declaration. The release unit must keep every materializable context materializable.

## Design constraints from this evidence

The selected design must distinguish a supported treatment omitted by a selected profile from an intrinsically unsupported role/property. It must record the former as an actionable informational fact and reject the latter at Theme load/closure. It must also count Layout's suppressed plot-label placements without making Scene or the adapter re-run placement. Tests must cover both baseline and rich target profiles, direct and Scheme bindings, Text/Path/Icon serialization, bundled resources, CLI projection, Scene diagnostics, and user-visible SVG/PNG output.
