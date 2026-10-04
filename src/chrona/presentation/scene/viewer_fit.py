"""Which output targets honour a box role's viewer-fit mode (#1050), and the warning for those that do not."""
from __future__ import annotations

from chrona.presentation.scene.model import SceneSurface

# SVG writes both modes. PNG and PDF draw the packaged font from the `raw` SVG, so there is nothing to absorb and
# no request fails. Typst and TikZ have no verified way to pin a run's advance or to size a box from a rendered run:
# they draw the static box and the lines as always, and the declaration is reported by role.
UNHONOURED_TARGETS = frozenset(("typst", "tikz"))


def viewer_fit_fallbacks(surface: SceneSurface, target_kind: str) -> tuple[str, ...]:
    """One ``W_VIEWER_FIT_NOT_HONOURED:<box role>:<target>`` per distinct non-raw box role, in Scene order."""
    if target_kind not in UNHONOURED_TARGETS:
        return ()
    roles = dict.fromkeys(item.visual_role for item in surface.primitives
                          if item.viewer_fit != "raw" or (item.text_layout is not None and item.text_layout.fit is not None))
    return tuple(f"W_VIEWER_FIT_NOT_HONOURED:{role}:{target_kind}" for role in roles)
