# ADR-0014: DateTime successor uses instant plus IANA zone

**Status:** Accepted for proposed v0.2 design

## Decision

DateTime stores an authoritative instant and supplied IANA zone. Local input requires
explicit DST disambiguation; gaps reject. Date-only v0.1 remains unchanged and is not
midnight-extended.

## Consequence

ExactDuration is elapsed-time arithmetic, while CalendarPeriod is zone-local calendar
arithmetic. Implementations require v0.2 schemas and fixtures before enabling it.
