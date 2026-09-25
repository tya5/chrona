# Design Correction Plan — Project-Format Package Requirement (#405, #406, #407, #408, #400)

**Trigger:** I1 materialization found that a profile package pins
`requires.projectFormat: timeline/v0.6`. Project v0.7 cannot be adopted while
that package contract remains v0.2.

1. Publish the profile-v0.3 migration decision and architecture review.
2. Amend I1 to migrate every package requirement and reference identity with
   project-v0.7/view-v0.17 in the same release.
3. Resume materialization only after the closed package requirement is current.
