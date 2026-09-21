# Issue 38 Implementation Plan

**Status:** Ready
**Design source:** Specification 40.

1. Extend `materialize_example` Context acceptance to v0.5/v0.6 and copy closure resources by each reference revision, including nested Snapshot Projects.
2. Update Context acceptance tests to select v0.5/v0.6 schemas and verify all closure references.
3. Regenerate changed example Context identities and expected SVG only through the public materializer.
4. Run every declared example integration test and add it to CI.
5. Recover only verifiable non-empty historical documents; publish the implementation review and close #38.
