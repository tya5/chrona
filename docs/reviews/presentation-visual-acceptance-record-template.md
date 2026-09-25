# Presentation Visual Acceptance Record Template

Use this section in the acceptance review for a change that affects
presentation vocabulary, treatment, Layout composition, or generated
presentation artifacts. It records a human review of reproducible output; it
does not replace byte checks or become a runtime resource.

## Record

* **Input commit:** `<full commit identity>`
* **Reviewer:** `<name or accountable role>`
* **Generation command:** `<exact materializer or gallery command>`
* **Artifact set:** `<declared Contexts, gallery entries, and output paths>`
* **Observed intended difference:** `<what changed and why>`
* **Accessibility / semantic distinction:** `<what remains machine-readable or visually distinguishable>`
* **Non-goals and unchanged output:** `<explicit exclusions and byte-diff result>`

The artifact set must be declared corpus/gallery evidence and the command must
be reproducible from the stated commit.
