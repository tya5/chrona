# Issue 370 design plan

## Objective

Turn four recurrent reject-or-silence defect classes into deterministic,
reviewable populations: diagnostic actionability, declared-versus-computed
values, executable command documentation, and corpus magnitude.

## Design sequence

1. Inventory existing gate conventions, CLI grammar, diagnostic construction
   boundaries, identity checks, corpus discovery, and documentation command
   forms. Separate facts derived from the tree from classifications requiring a
   maintainer decision.
2. Define a single checked-in policy source for each human classification:
   user-facing bare diagnostic allowlist, declared-versus-computed site labels,
   documented command fixtures, and corpus magnitude thresholds. Generated
   reports must derive their populations and show unclassified members.
3. Define extraction rules that are deliberately conservative and stable:
   AST for diagnostic construction and identity comparison, parser metadata for
   CLI forms, and manifest/Context facts for corpus scale. Avoid interpreting
   arbitrary Python execution.
4. Review the gates against Core/operational/application architecture. The
   gates must neither weaken immutable identity assertions nor turn generated
   documentation into runtime authority.
5. Publish the design and review, then create an implementation plan whose
   slices independently introduce reports, policy classifications, gates, and
   CI integration.

## Required acceptance evidence

- A generated diagnostic inventory names every discovered code/site/layer and
  reports actionability; a narrow ingress gate rejects unclassified bare sites.
- Every computed-vs-declared comparison site has a checked-in classification;
  deliberately pinned values name a public producer or are rejected.
- Every documented CLI invocation is parsed against the real CLI grammar, and
  the documented fresh-project sequence executes in a temporary directory.
- Corpus coverage includes deterministic per-corpus magnitude facts and checks
  declared contract thresholds.
- The reports, policy documents, focused tests, conformance, full suite, and
  CI are all published before #370 is closed.
