# Architecture Review: Slot-owned icon placement correction (#375)

**Decision:** Approved.

The correction restores the placement closure promised by Scene v0.2.  Icon
ownership is geometry-adjacent allocation policy, so it belongs to Layout with
the host placement rather than to Scene or the coverage reader.  Resolving the
group-header alias to its table slot is a Layout fact, not a rendering
heuristic; explicit annotation-slot ownership follows the same rule.

The design deliberately retains optional annotation slots.  Requiring them to
support unrelated label visuals would distort Layout profiles and hide the
actual owner.  The explicit pre-projection invariant is the correct structural
guard against recurrence.
