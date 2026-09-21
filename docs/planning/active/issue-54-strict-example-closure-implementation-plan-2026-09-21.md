# Issue #54 strict example-closure implementation plan

1. Add strict completeness validation to the materializer copy path for all resource and font
   references, preserving authored bytes and existing mismatch diagnostics.
2. Add focused negative tests for missing and wrong resource/font pins, asserting no SVG write.
3. Merge the PR #53 pin-only context declarations after confirming its head SHA.
4. Re-run full pytest and all five check-mode materializations; record exact results on #52/#54.
5. Close #49 and #54 only when the post-merge gate is green.
