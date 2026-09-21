# #41 設計レビュー（2026-09-21）

承認。

- ReviewRow remains the only grouping/membership owner; member labels are derived Scene primitives.
- fixed mark size comes from resolved Theme metrics, preserving View/Theme/Scene separation.
- relation routing uses per-mark ports, preventing invalid one-point renderer paths.
- snapshot receives a current Theme semantic role rather than restoring deleted Settings/legacy Theme contracts.
- callout rail uses the existing annotations Layout slot and annotation resource; no parallel authoring model is created.
- #42 remains the owner of additive slide vocabulary.
