# C-GDF-1 Corpus Hygiene and Preset Evidence Design Review

**Decision:** Accepted

The correction preserves the corpus/materializer boundary: declared Contexts
remain the only closure authority and generated SVG remains the only public
render evidence. The preset is parsed as an existing ordinary resource
declaration and cross-checked against Context identities; it does not activate
guided authoring or a package resolver. Removing undeclared variants reduces,
rather than migrates, competing rendering authority. This is consistent with
Specifications 32, 51, 55, and 58.
