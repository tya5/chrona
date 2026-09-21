# M27 Example Materializer Manifest Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R5 materializer implementation is authorized.

The existing ASTER manifest is an informal source list and Controller Z has none. A
generic v0.5 materializer needs one explicit manifest contract rather than inferred
repository paths. Each manifest declares a version, example ID, the Context reference
source, and a named set of slides with a declared expected SVG target. The Context is
the sole closure selector; a slide selects only an expected target and may not replace
the Context's View/Theme/Layout resources.

The manifest's Context field names the raw Context resource path. The materializer
copies it into the temporary snapshot and derives its immutable resource reference
with the exact raw-byte content identity; that derived reference is then the only
argument supplied to `chrona render-review`. `--check`
compares the derived SVG with the named expected target; `--write` replaces only that
target. A manifest missing Context/snapshot/slide/target, or a target outside the
example root, is rejected. This makes the materializer generic without giving examples
a parallel resource model.
