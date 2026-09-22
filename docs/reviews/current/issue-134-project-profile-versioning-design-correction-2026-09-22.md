# Issue 134 Project/Profile Versioning Design Correction

## Trigger

Project v0.3 is referenced immutably by Profile v0.1 through
`requires.projectFormat`. Moving Project to v0.4 while editing Profile v0.1
would give the same profile version a different applicability contract.

## Corrected decision

Project v0.4 and Profile v0.2 are an atomic dependency migration. Profile v0.2
changes only its declared required Project format to `timeline/v0.4`; profile
semantics do not otherwise change. The schema registry, extension loader,
inventory, documentation, profile resources, conformance validators, runtime
fixtures and Context references migrate together. Project v0.3 and Profile
v0.1 receive no compatibility parser.

View v0.6 follows only after that Project/Profile migration is merged. This
prevents a period where a materializable current Project has no compatible
validated profile package.

## Architecture review

Profile packages are immutable validation inputs to closure, not a presentation
escape hatch. This correction preserves the Project -> profile requirement ->
closure direction and makes the typed-link extension a Project contract change
rather than an unvalidated field accepted by an old profile format.
