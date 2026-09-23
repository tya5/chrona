# Issue #347 Closure Learnability and CI Remediation Design Plan

## Verified scope

The post-hoc review correctly found that presentation closure conversion drops
the already-computed schema explanation.  The review's claims about
`items`/`oneOf`/`anyOf` traversal are superseded by the current annotation
applicator correction; `then`/`else` traversal remains to be audited.  #322's
accepted alternative example-role decision is missing from the original Issue
conversation.  CI still performs an unnecessary full-history checkout, has no
dependency cache, and double-triggers same-repository pull-request commits.

## Design work

1. Define a diagnostic-detail carrier from `SchemaContractError` through
   `ClosureError` to the CLI, retaining stable public error IDs and pointers.
2. Audit every JSON-Schema applicator traversal, distinguish a genuine blind
   spot from wrapper-level annotation coverage, and define the smallest
   recursive lint correction with negative fixtures.
3. Review CI trigger, checkout, cache, matrix, and shared-render-fixture
   changes against deterministic materializer and cross-platform evidence.
   Do not cache or share mutable repository fixtures.
4. Record #322's already accepted alternative decision in its Issue discussion.
5. Publish design and architecture review before implementation planning.

## Completion criteria

Author-facing closure diagnostics carry the selected explanation; the lint
cannot hide authorable nodes under any supported applicator; CI work removes
unnecessary duplicate/setup cost without weakening required platform coverage;
and Issue #322 links its closure to Specification 58.
