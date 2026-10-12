# Previous-Scene semantic ports (#1300)

Scene v0.7 records endpoint instance IDs and unrounded points, not selected
egress-side IDs. A route tangent is not proof of that side: a point's left port
may be approached vertically, and a span's temporal port admits several egress
corridors. Do not claim reconstruction of an identity the artifact never carried.

Uniquely recover the prior semantic endpoint coordinates from host geometry and
terminal trimming. Retain the point/body boundary choice where geometry identifies
it. Reanchor that route without changing its shape family or interior channels.
For the current input, enumerate admitted egress pairs in the existing first-fit
order; test compatible proposals through the same completed-candidate validator.
The first accepted current pair wins before ordinary proposals/search. Multiple
legal current pairs are an ordered choice, not an ambiguous historical identity.
Ambiguous prior semantic coordinates still produce an unusable hint.

Architecture review: no Scene extension, fake ID, renderer inference or second
validator. Layout owns reconstruction, ordered proposals and acceptance. Existing
port admission, host corridors, bounds, terminals, quality and window safety stay
hard. Best/no-hint results are unchanged; original stability/critical criteria
remain independent. Normative authority: Specification50's previous-Scene rule;
implementation amendment: the living #1300 work plan. Tests cover point-port
arrival direction, multiple current egress choices, same-input no-search counters
and the actual v1/v2 adapter output. No examples changes.
