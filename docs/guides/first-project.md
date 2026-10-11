# First project

Start with an editable plan, not a copied corpus:

```bash
chrona init my-first-chrona-project
chrona render my-first-chrona-project/project.yaml \
  --actual my-first-chrona-project/actual.yaml \
  --output my-first-chrona-project/plan.svg
```

`project.yaml` contains two tasks and a gate.  Change their titles, dates, or
add objects and relations; `actual.yaml` holds observations for the same object
identifiers.  The command uses Chrona's packaged `chrona-default-draft`
presentation preset.  The SVG is a Draft review artifact, not immutable
materializer evidence. The omitted viewport uses the Draft `1600xauto`
default; use an explicit finite viewport when its minimum size matters.
The output filename also selects the format: `.svg`, `.png`, `.pdf`, `.typ`
and `.tex` select SVG, PNG, PDF, Typst and TikZ respectively. Without a
suffix, Draft defaults to SVG. An explicit `--format` must match a recognized
suffix; unknown suffixes are rejected before writing output. Typst and TikZ
still require their typesetter descriptor flags.

To select a supplied appearance explicitly, copy one into your own source tree
and render through its ordinary local preset.  Available ids are
`mission-light`, `control-room-dark`, `print-mono`, `executive-light`, `elevated-light`, `editorial`, `technical-print`,
and `chrona-default-draft` (the look used when no preset is named); `chrona preset list` prints them.

```bash
chrona preset copy control-room-dark --output my-first-chrona-project/looks/control-room-dark
chrona render my-first-chrona-project/project.yaml \
  --actual my-first-chrona-project/actual.yaml \
  --preset my-first-chrona-project/looks/control-room-dark/preset.yaml \
  --output my-first-chrona-project/plan.svg
```

The copied `preset.yaml`, `view.yaml`, `theme.yaml`, `scheme.yaml`, and
`layout.yaml` are ordinary editable files. All supplied looks render
with the default SVG profile. `elevated-light` uses a visible flat fallback
there; select `--visual-profile chrona-output/visual/v0.7-svg` explicitly
when you want its gradient and shadow treatment.

To draft a schedule faster than editing YAML, write a [terse plan](terse-plan.md): a `plan.chrona` file with one
line per task, gate or group. `chrona render`, `validate` and `schedule` accept it where they accept `project.yaml`,
and `chrona compile` turns it into the Project once it is final.

To learn Project capabilities in small independent steps, follow the
[progressive Project tutorial](progressive-project-tutorial.md).

An AI coding agent can follow the same path from the [chrona agent skill](../../skills/chrona/SKILL.md),
which carries the authoring model, a worked plan, the diagnostic codes an agent meets and
when to use Mermaid instead.

## Change two Theme tokens without copying the whole Theme

[This five-line derived Theme](../../examples/aster-ssd/themes/onboarding-variation.yaml)
replaces only `heading-size` and `text-size` in ASTER's complete Theme. Its
`extends` declaration pins both the exact base file bytes
(`sourceContentIdentity`) and the complete base Theme's canonical identity
(`contentIdentity`). It resolves before rendering to an ordinary Theme; it is
not an arbitrary YAML merge, and unknown token names are rejected. Keep the
base file beside the derived file, and update both pins deliberately if the
base changes.

These two Draft renders use the same Project, View, Scheme and Layout. The
derived output has a 30 px title and 16 px table header, versus 24 px and
14 px in the base output.

<!-- chrona:doc-check requires: clone the commands read files that only a clone of the repository has (examples/ is not in the wheel) -->
```bash
chrona render examples/aster-ssd/project.yaml \
  --view examples/aster-ssd/views/01-overview.yaml \
  --theme examples/aster-ssd/themes/executive-light.yaml \
  --scheme examples/aster-ssd/schemes/executive-light.yaml \
  --layout examples/aster-ssd/layouts/executive-review.yaml \
  --actual examples/aster-ssd/actual.yaml --output aster-base.svg
chrona render examples/aster-ssd/project.yaml \
  --view examples/aster-ssd/views/01-overview.yaml \
  --theme examples/aster-ssd/themes/onboarding-variation.yaml \
  --scheme examples/aster-ssd/schemes/executive-light.yaml \
  --layout examples/aster-ssd/layouts/executive-review.yaml \
  --actual examples/aster-ssd/actual.yaml --output aster-derived.svg
```

For a complete materialized regression corpus instead, request it explicitly (from a clone with
`pip install -e packages/chrona-fonts-noto-cjk`; an installed wheel does not carry that font package yet):

<!-- chrona:doc-check requires: clone init --example halcyon-1 needs packages/chrona-fonts-noto-cjk, which a wheel does not install -->
```bash
chrona init my-halcyon-corpus --example halcyon-1
```

That example's immutable closure lives in `.chrona/store`; it is runtime state,
not source to edit.  See the [root README](../../README.md) for its public
materializer command.

### Render an example Context from its Store

`chrona init --example` copies the example's Contexts into `.chrona/store`.
`render-review` renders one from an immutable resource reference to it.  Write
that reference by hand: `id`, `store` and `revision` come from the Context's
`body.project`, `kind` is `render-context`, and `address` is the Context's path
in the Store.  `--store-config` points the command at the Store `init` wrote, so
no `--snapshot-root` or `--store-identity` is needed:

<!-- chrona:doc-check skip: the reference file is written by the heredoc in the same block -->
```bash
cat > my-halcyon-corpus/context-reference.yaml <<'YAML'
id: halcyon-1-01-mission-brief
kind: render-context
store:
  provider: local
  identity: halcyon-1-example
address: contexts/01-mission-brief.yaml
revision:
  token: example-v4
YAML
chrona render-review \
  --context-reference my-halcyon-corpus/context-reference.yaml \
  --store-config my-halcyon-corpus/.chrona/store.yaml \
  --output my-halcyon-corpus/mission-brief.svg
```

The Store config names its Store relative to itself (`root: store` in `.chrona/store.yaml`),
so the whole directory can be moved, copied or committed and `--store-config` keeps
working. A config written by an older `chrona` holds an absolute `root`: it still works
where it was made, and replacing the value with `store` makes it relocatable.

Content identity is required by default for every Store (Spec 42), and the
example Contexts leave their inner references unpinned by design (ADR-0030).
So `init --example` writes `integrity: optional` into `.chrona/store.yaml`, with
a comment saying why.  That exception covers the example corpus only: a Store
you create yourself, and an `integrity` you omit, stay `required`; for one call
on such a Store, `--allow-missing-content-identity` is the explicit opt-out.
