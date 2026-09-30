# Design — Packaged Defaults Independent of Corpus Examples (#574)

**Plan:** [design plan](../planning/active/issue-574-packaged-defaults-independent-of-corpus-design-plan-2026-09-30.md).

## Decisions

1. **The presets root owns everything a preset needs.** `default_preset_root()` returns `files("chrona.resources") / "presets"`. `presets/default.yaml` uses paths relative to it. The default reuses the Editorial bundle's `scheme.yaml`, `layout.yaml` and `detail.yaml`, because they are the same resources the default already names (`chrona-builtin-editorial`, `chrona-builtin-editorial-detail`). Its two readable-default resources become `presets/bundles/default/view.yaml` and `presets/bundles/default/theme.yaml`, with unchanged ids and bytes.
2. **Every catalogue scheme is packaged.** Each of `mission-light`, `control-room-dark`, `print-mono`, `executive-light` and `elevated-light` gains `bundles/<id>/scheme.yaml` with unchanged id and bytes, and its library entry points its `colorScheme` member at that bundle. `executive-light` and `elevated-light` each carry their own copy, as every bundle already carries its own View, Theme and Layout.
3. **The package is authoritative.** An example that still uses one of these schemes keeps its own file, because committed Contexts pin it. A drift test asserts each such example file is byte-identical to the packaged one, the direction already used for Editorial. An edit to an example can no longer change a packaged preset; it fails the drift test instead.
4. **No path under `examples/` is reachable from preset resolution.** `builtin_preset_source_root` refuses a root that does not start with `presets/` or `icons`. The `examples` branch and the halcyon fallback in `default_preset_root` are removed. `examples` stays a packaged directory only for `chrona init --example`.
5. **`--example` reads a registry.** A packaged `example-registry.yaml` (kind `example-registry`, `example-registry-v0.1.schema.yaml`, listed in the schema inventory) names the initialisable examples, each with an id, a packaged path and a one-line purpose. `chrona init --example` takes its choices from it and reports the available ids in `E_INIT_EXAMPLE`. Its only entry today is `halcyon-1`. The wheel ships exactly the registered examples, so `examples/controller-z` leaves the force-include list once nothing packaged reads it.
6. **`gallerySet` is documented as grouping only.** The values keep their names because committed gallery pages use them. The `preset-library` schema description says a gallery set groups evidence, selects no resource and has no runtime effect.

## Test for "examples absent"

A unit test wraps `chrona.resources.files` so that any path starting with `examples`, and the top-level `examples` package, raises. It then renders the bundled default and every library entry (`chrona preset copy`, then `render --preset`) against a synthetic project written in a temporary directory. A wheel build in every run would cost minutes; the existing wheel smoke step keeps covering the installed package.

## Boundaries

Resources and packaging only. No Layout, Scene or adapter change, and no schema change except the new registry schema. Rendered bytes are identical before and after the move (the acceptance row), which is a no-change proof for a resource move and not a quality claim.
