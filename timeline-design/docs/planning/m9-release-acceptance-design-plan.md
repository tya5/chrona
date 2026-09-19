# M9 Release-Acceptance Design Plan

**Status:** Complete — design gate before M9 release implementation

## Goal

Make a current-profile release claim reviewable without treating successful SVG output
as proof of unrelated user outcomes.

## Design decisions

1. A release manifest binds an immutable input closure and declared output target/version.
2. It enumerates UC-01 through UC-15 exactly once, as `accepted` with reproducible
   evidence or `excluded` with a reason and owner.
3. Excluded is non-acceptance. M9 cannot close with exclusions because its roadmap exit
   requires coverage of all current-profile use cases.
4. The design fixture is validated against the JSON schema, exact use-case set, and
   local evidence paths as part of repository conformance.

## Implementation sequence after this gate

1. Implement the missing M5 AI Command-proposal adapter and policy integration for UC-06.
2. Add runtime release-packaging validation that checks output-manifest evaluation
   identity and target/version against this manifest.
3. Run the full test and conformance suites, then conduct the M9 reuse/release review.
