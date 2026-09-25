# Implementation Plan — Shared-Track Order and Summary-Bar Geometry (#417)

1. Add the one model policy function and replace every inline shared-track
   source-kind mapping in `surface_composer`, layout presentation helpers and
   Scene.
2. Add `ThemeTokenView.summary_bar_height()` and bind `markHeight` on the
   existing `summary-bar` role in every shipped Theme; validate positive values.
3. Compose summary-bar height from that token and characterize source ordering
   plus token-controlled completed bounds.
4. Regenerate the corpus, run focused tests, full pytest, presentation/corpus
   coverage, schema-reference validation, public materializer byte checks and
   generated SVG review.
