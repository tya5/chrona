# Actual Set v0.2 Completion Design Plan

P7 closure found that Actual Set v0.1 carries Context-relevant `asOf` and
unmatched external observations, while v0.2 requires immutable external
provenance but omitted `asOf`.  Complete this semantic migration before v0.1
removal: preserve both facts in v0.2, migrate all authoring fixtures, then
remove the superseded route and re-run the final inventory gate.
