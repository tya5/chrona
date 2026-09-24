# Wheel Resource Topology and Installed-Wheel Evidence Design (#379, #381)

## Decision

Each runtime resource has one authored source.  The HALCYON init template is
authored solely at `examples/halcyon-1/` and force-included into the wheel as
`chrona/resources/examples/halcyon-1/`, matching the existing schema pattern.
`chrona.resources` owns selection between its installed resource and the
development-source resource; `local_authoring` asks only for a named template
and never learns where a wheel or checkout stores it.

Installed-wheel smoke uses a finite, explicit public-journey matrix.  A row
must open its claimed resource bytes and assert an observable result.  This is
more meaningful than listing directories and ensures a resource cannot be
declared covered merely because the package can enumerate it.

## Resource selection

Add a resource-layer helper for supported init templates:

```text
template_resource("halcyon-1")
  → chrona.resources/examples/halcyon-1 in an installed wheel
  → examples/halcyon-1 through importlib.resources in source development
```

The helper checks that the selected item is a directory and returns a
`Traversable`.  It does not derive paths from `__file__`, current working
directory, environment variables, or an arbitrary checkout.  The source
alternative is available only because editable development deliberately exposes
the repository root (`dev-mode-dirs = ["src", "."]`), the same declared model
already used by `schema_resource()`.  An unsupported template keeps
`E_INIT_EXAMPLE`; no search or compatibility reader is introduced.

`initialize_project()` retains non-overwrite behavior and its post-copy
immutable Context closure creation unchanged.  Only its template source moves
behind the resource boundary.

## Build topology and deletion

Hatch receives this explicit mapping:

```toml
"examples/halcyon-1" = "chrona/resources/examples/halcyon-1"
```

The checked-in `src/chrona/resources/examples/` copy is deleted.  So are
`tools/check_init_template.py` and its conformance invocation: a synchronization
gate is not a substitute for one authority.  Source tests exercise the source
resolver; isolated wheel smoke exercises the forced resource.

## Installed-wheel resource matrix

| Resource tree | Public journey | Observable proof |
| --- | --- | --- |
| `schemas` | validate/schedule a Draft | schema resource resolves and semantic validation succeeds |
| `examples` | `chrona init` then `chrona materialize` | initialized manifest and materialized SVG exist |
| `font_metrics` | same materialization | declared metrics participate in Context rendering |
| `icons` | `chrona icon-catalog material-default` | non-empty normalized catalog with its declared contract header is written |
| `fonts` | Draft `chrona render --format png` using initialized authored resources | PNG signature is written; rasterization resolves and identity-checks declared TTF bytes with system fonts disabled |

The PNG command uses copied initialized inputs and only temporary output.  It
does not turn a Draft render into public materializer evidence.  The smoke tool
continues to run outside the checkout after the built wheel is force-installed.

## Error and ownership boundaries

- Resource selection belongs to `chrona.resources`; init owns only accepted
  template names and file-copy semantics.
- Icon and font resource opening stays behind existing public CLI commands;
  smoke adds no private resource API or test-only renderer path.
- The source fallback is development-only resource resolution, not a runtime
  fallback for an installed wheel.  A wheel missing a forced template fails its
  installed smoke rather than finding the repository.
- No Project, Context, Layout, Scene, renderer policy, or materializer input
  contract changes.

## Acceptance

- No duplicate init-template tree or synchronization gate remains.
- Source and installed-wheel `chrona init` both produce a materializable
  project from the same authored HALCYON bytes.
- Every current runtime resource tree has an explicit installed-wheel smoke
  matrix row with a byte-opening public behavior assertion.
- Focused tests, conformance, materializer byte reproduction, wheel smoke, and
  three-platform CI remain green.
