# Implementation amendment — suppression identity closure (#458)

**Correction:** [design correction](../../design/issue-458-suppression-identity-closure-correction-2026-09-26.md).

Extend `scene/perceptibility.py` to map the three exact suppression diagnostics
to their Scene primitive IDs. Add focused fixtures for all three and a
nonmatching relation ID. Refresh diagnostic inventory, run the corpus gate,
public materializer reproduction, and conformance; inspect the generated
diff, which should be empty for this observer-only amendment. Publish the
correction separately from acceptance review.
