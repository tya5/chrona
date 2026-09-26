# Implementation Amendment — Derived Theme Materializer Closure (#378 I378-2)

**Design correction:**
`issue-378-theme-inheritance-materializer-closure-correction-2026-09-26.md`.

1. Complete the shared ingress resolver and safe child-reference constructor
   in `presentation/model/theme_inheritance.py`. The loader separates source
   bytes from decoded value; tests cover both pins, recursion, traversal,
   cycles, unknown replacements, and ordinary v0.11 identity preservation.
2. Connect Draft and Context source loading in `presentation/model/closure.py`
   to that resolver. No derived form may enter `parse_contract` or the final
   RenderClosure. Use the snapshot reader for every Context source edge.
3. Make `usecases/materialize.py` recursively copy the Theme base edge using
   the same child reference and verify its source pin before snapshot write.
   Add a public-materializer integration fixture with a derived Theme; prove
   the base is copied and tampering is rejected.
4. Refresh schema, diagnostic and declared-value inventories once after the
   source changes. Run focused resolver/closure/materializer tests and all
   declared public materializer byte checks. Publish an implementation slice,
   then proceed to the tutorial and literal #378 acceptance gate.

Each step follows the published T378/A378 acceptance conditions. The new
materializer fixture is a required proof, not an optional example.
