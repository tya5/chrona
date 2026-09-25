# Implementation Amendment: Source observations in the capability matrix (#390)

Replace the source-list-only matrix with a finite source registry and complete
per-capability observation table.  Render a Chrona disposition column and one
column per external source, including source links in headings and a legend.
Add focused tests for complete coverage, stale capability/source detection,
and the three-value observation vocabulary.  Regenerate the public matrix and
run its check before resuming I390 release verification.
