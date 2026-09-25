# Architecture Review — Fiscal Calendar Contract (#405, #406, #407, #408, #400)

**Result:** Accepted.

Fiscal origin is a calendar fact, so it belongs with the working-day and
exception facts that already make up the Project calendar. The View selects a
presentation tier; Layout derives intervals from the closed Project fact;
Scene/adapters receive completed intervals. The versioned atomic migration
keeps immutable closure identity truthful and avoids a locale-derived fallback.
