# Issue #347 Closure Learnability and CI Remediation Implementation Plan

1. Extend `ClosureError` with optional detail and pass selected schema
   explanations at all Draft/immutable Context conversion sites.  Add CLI and
   closure tests proving stable ID, pointer, and allowed-value prose coexist.
2. Recurse through `if`, `then`, `else`, and `not` in the annotation linter;
   add negative fixtures for hidden conditional nodes and annotate any live
   nodes newly discovered by the gate.
3. Optimize the conformance workflow's trigger, checkout, and dependency cache
   without changing its matrix, gate order, or test command.  Do not add a
   shared render fixture.
4. Record #322's accepted alternative decision on GitHub.  Run focused tests,
   conformance, full pytest, public materializer byte checks, and wheel smoke;
   publish acceptance evidence and close #347.
