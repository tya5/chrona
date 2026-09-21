# Chrona examples

Each directory is one runnable project. Source facts are stored once at the project
root; presentation-specific inputs and deterministic outputs are nested below a variant
or slide directory.

| Project | Purpose |
|---|---|
| [`controller-z/`](controller-z/) | Compact silicon bring-up project rendered through multiple presentation directions. |
| [`aster-ssd/`](aster-ssd/) | Larger SSD program rendered as a five-view presentation gallery. |
| [`halcyon-1/`](halcyon-1/) | Smallsat mission rendered three ways — briefing, dark wall board, print portrait — from one plan; regenerated with `tools/materialize_example.py`. |

Files named `expected.svg` are deterministic acceptance artifacts. `preview.png` is a
raster review artifact. Edit YAML sources, regenerate the output, and verify the exact
result with the corresponding acceptance tests.

Project, Actual, View, Theme, Layout, and optional review profiles stay
in separate files so reusable presentation resources are not copied into Project data.
See the [render-review YAML layout guide](../docs/guides/render-review-yaml-layout.md)
for the current authoring/generated boundary.
