# Example Curriculum

The public examples are regression corpus first.  This guide is a learning path
over those same declared resources; it does not introduce another source format
or a separate rendering command.

1. Start with [Controller Z](../../examples/controller-z/README.md) to render a
   plan and actual review from explicit Project, View, Theme, Scheme, and Layout
   inputs.
2. Read the [ASTER SSD example](../../examples/aster-ssd/README.md) for a
   plan-only, calendar-aware project.
3. Use HALCYON's `mission-brief` as the progression to immutable Context
   materialization and multi-slide review evidence.

The validated curriculum catalogue is `example-curriculum.yaml`.  For byte
reproduction and public evidence, use the manifest and public materializer,
not this guide.
## Scale curriculum

The curriculum includes a committed 30-row Draft Project at
`examples/controller-z/curriculum/scale-30.yaml` and integration coverage for
the corresponding 100-row case. They exercise `chrona render --viewport
1600xauto`: Layout resolves a finite viewport from measured rows before Scene
and output generation. For reproducible published evidence, select an explicit
height returned by that command and materialize a fixed Context; immutable
Contexts never accept `auto`.

Run the 30-row Draft with the Controller Z executive presentation inputs and
its required Actual Set:

```sh
chrona render examples/controller-z/curriculum/scale-30.yaml \
  --view examples/controller-z/views/executive.yaml \
  --theme examples/controller-z/themes/executive-light.yaml \
  --scheme examples/controller-z/schemes/executive-light.yaml \
  --layout examples/controller-z/layouts/executive-review.yaml \
  --actual examples/controller-z/actual.yaml \
  --viewport 1600xauto --output curriculum-scale-30.svg
```

The output has 30 rows and a measured `2357`-pixel block extent.  The generated
Draft SVG is a local learning artifact, not immutable public evidence.
