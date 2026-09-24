# Issue 370 resolvability quality gates architecture review

## Result: accepted for implementation planning

The design treats quality evidence as a derived, reviewable repository
population.  It does not add a second diagnostic model, an identity resolver,
a documentation-defined CLI, a corpus runtime configuration path, or a
presentation authority.  The policy records only decisions that static
analysis cannot make; exact codes classify the stable diagnostic interface
while the generated report retains every affected source site.

## Boundary findings

| Review question | Result |
| --- | --- |
| Does the diagnostic gate make source-code syntax product authority? | No. It detects absence of detail at ingress and leaves emission to the existing owner. |
| Does declared-versus-computed analysis weaken immutable pins? | No. `pinned-deliberately` retains the assertion and requires a public producer. |
| Can Markdown define a CLI surface? | No. Live argparse metadata is authoritative; Markdown is validated against it. |
| Does executable documentation turn repository docs into runtime input? | No. The wheel-smoke harness owns a named temporary sequence independent of docs parsing. |
| Does magnitude couple corpus to SVG or Layout implementation? | No. Facts derive from semantic declared resources and declared contract limits only. |
| Are classifications reviewable and complete? | Yes. Exact policy codes, source-site inventory, and stale-entry rejection make the full derived population visible. |

## Required implementation constraints

1. A code exception is allowed only when it is the complete message across
   every bare ingress site; source-varying errors must carry detail.
2. Keep AST extraction conservative; unknown construction/comparison forms
   must be reported and classified rather than guessed away.
3. Keep policy parsing in `tools/`/`conformance`; `src/chrona` must not import
   it.
4. Make `--check` generated-report comparisons byte deterministic.
5. Add parser-introspection tests that include nested commands and aliases.
6. Keep the installed-wheel fresh-project execution in the post-install CI
   phase, not in repository-only conformance.

The design is consistent with Core identity ownership, adapter/use-case
separation, and the presentation pipeline.  The implementation plan may now
define independently reviewable rollout slices.
