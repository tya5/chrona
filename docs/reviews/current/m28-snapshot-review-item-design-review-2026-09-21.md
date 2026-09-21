# M28 Snapshot Review Item Design Review — 2026-09-21

**Decision:** Design correction complete; implementation planning is authorized.

The cross-boundary review found and corrected the only missing dependency: Snapshot
Review Items now require an explicit v0.6 Render Context → snapshot-ref → immutable
Project closure. The resolver independently schedules both immutable Projects and
records their distinct revisions, while retaining the stable Project-ID alignment rule.

Review rows and items remain View-owned. Project, Snapshot, and Actual meanings are
unchanged; Layout owns row geometry; Scene owns subtracks; SVG receives only completed
primitives. There is no legacy Settings restoration, moving branch input, or copied
schedule data. M28 design is now complete.
