# Architecture Review: Self-contained preset roots (#377)

**Decision:** Accepted.

Allowing parent traversal or two relative-path meanings would create an
ambient project edge and make installed-wheel/default resolution differ from
user-owned presets.  A closed root instead preserves the existing safe-path
contract and leaves Context/materializer resource authority unchanged.  The
required presentation-resource duplication is an explicit preset closure, not
a second Project source or a package acquisition mechanism.
