# Design correction — programme-board annotation fallback (#504)

R2's `fill` rows and complete member-name placement expose a conflict in the shared 02/11/12 View: the three plot notes declare only a tail-connected `nearest-free` candidate. When its finite tail-route search is exhausted, the existing visible-overflow fallback may paint the annotation box over required member names. Public Scene perceptibility rejects those intersections. This is a resource policy gap, not a reason to suppress names or broaden Scene geometry ownership.

Keep the tail-connected candidate first. Add a second declared `nearest-free` plot candidate with the same measured width and obstacle classes but `connector: none`. Layout accepts that box only if it clears the completed marks, text, visuals, routes, other annotation boxes, ports, and rule. The absence of a tail is an explicit presentation fallback, recorded by the existing candidate-fallback diagnostic; it does not alter the annotation content, anchor identity, lane membership, or public schema. The shared 02 View supplies the policy to 02/11/12. No engine condition or adapter repair is needed.

Acceptance requires 26/26 member names, zero name suppressions, no Scene text intersections or occlusions, and passing public materializers on 02/11/12. Other slides remain byte-identical.
