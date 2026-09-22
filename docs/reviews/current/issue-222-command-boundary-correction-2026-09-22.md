# Issue 222 Command Boundary Correction

## Trigger

I222-3 exposed that placing guided-workspace normalization in the operational Command
Engine would invert the application dependency direction: `operational` would import
the presentation-model normalizer. That violates Specification 09 and the repository's
import-direction gate.

## Corrected integration

The Command Engine remains the sole transport, compare-and-set, result, replay, and
undo/redo boundary. An **Authoring Command Use Case** sits above it: it loads the named
workspace aggregate, applies one closed command intent, invokes the Authoring
Normalizer and existing semantic validation against the complete candidate, and gives
only validated canonical byte candidates plus the base revision to the Engine. The
Engine neither imports nor interprets authoring, preset, View, Theme, Layout, Scene, or
renderer types.

```text
CLI / GUI / AI -> Authoring Command Use Case -> Authoring Normalizer
                        |                         |
                        +---- validated bytes -----+-> Command Engine -> Store CAS
```

This is not a bypass: every mutation still crosses one Command Engine CAS transaction;
the use case is the typed application adapter required to preserve dependency direction.
Stage 3 supplies its complete resource candidate through the same boundary. Rejection
before or during CAS writes nothing.

## Result

The prior I222-3 implementation branch is not mergeable. Subsequent implementation
must place source-specific validation in `usecases`, retain a presentation-free
operational writer, and add a structural test that `operational` has no presentation
import.
