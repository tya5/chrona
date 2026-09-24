# Issue 366 implementation plan

1. Add the deterministic 30-row Project and README/curriculum references;
   execute its public `chrona render --viewport 1600xauto` command in tests.
2. Update Draft CLI help and README discovery text; test `--help` and the
   command's finite SVG result.
3. Refactor overflow detail assembly so Draft and immutable Context callers get
   correct remediation text; add Context and Draft characterization tests.
4. Add unsupported-surface detail, correct #365 records, run focused tests,
   full pytest, public materializer checks and CI, then release review/close.
