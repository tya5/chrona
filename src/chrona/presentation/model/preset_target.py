"""Draft ingress facts, separate from completed Scene presentation findings."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PresetVisualProfileFallback:
    preset_id: str
    preferred_profile: str
    selected_profile: str
    target_kind: str

    @property
    def code(self) -> str:
        return "I_PRESET_VISUAL_PROFILE_FALLBACK"
