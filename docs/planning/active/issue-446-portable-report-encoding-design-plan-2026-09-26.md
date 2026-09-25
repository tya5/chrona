# Design Plan — Portable Scene Report Encoding (#446)

The I446-2 release run passes Linux and macOS but Windows cannot encode a
non-ASCII public Scene identity through its default CP1252 stdout.  Define and
verify one explicit UTF-8 tool-output boundary for both human and JSON reports.
The correction must preserve evaluator facts, exit status, report ordering,
and no renderer/Layout dependency.
