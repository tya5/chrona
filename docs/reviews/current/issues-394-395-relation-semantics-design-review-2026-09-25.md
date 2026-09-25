# Relation semantics architecture review (#394, #395)

The design is accepted for implementation with the following boundary checks.

* Independent markers are completed Theme/Layout/Scene data, not SVG endpoint
  heuristics. Removing the singular marker avoids two competing authorities.
* Lag remains a Project scheduling fact. Projection preserves its declaration;
  Layout formats only the selected presentation content and never recomputes
  schedule arithmetic.
* Relation labels reuse the existing completed text/collision/overflow model.
  They do not use SVG `textPath`, whose adapter-specific geometry would bypass
  Layout measurement and suppression.
* Source order remains accessibility order while visual marker treatments are
  completed Scene values. The proposal adds no unbounded syntax, raw SVG, or
  compatibility reader.
* Corpus evidence must cover both terminal sides and signed lag, not merely
  schema acceptance. This satisfies the coverage failure pattern addressed by
  #392.

No conflict was found with the completed mark-composition program: relation
terminals are path-end treatments, while mark composition remains host-bound
geometry and paint ordering.
