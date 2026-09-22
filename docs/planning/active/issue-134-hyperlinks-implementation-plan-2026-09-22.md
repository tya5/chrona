# Issue 134 Typed Hyperlinks Implementation Plan

1. **Project v0.4.** Atomically migrate Project resources and validation to the
   typed object Link contract, including profile requirement and Context tests.
2. **View v0.6 and projection.** Atomically migrate View resources; normalize
   link modes and title columns; carry object link facts into primary review
   items and completed Scene selection metadata.
3. **Renderer gate.** Add escaped SVG wrappers, target invariance tests, public
   materializer characterization, generated-SVG review, and full pytest.

Each slice is independently published and merged with macOS/Ubuntu CI before
the next begins. Do not start #136 until #134 is closed.
