import pytest
from chrona.layout import resolve_layout_profile, solve_layout, validate_designer_preset

def profile():
    return {"version":"chrona/layout-profile/v0.1","id":"x","canvas":{"aspectRatio":"16:9","margin":"balanced","density":"review"},"regions":[{"id":"main","layout":"split"}],"slots":{"table":{"region":"main","source":"table","priority":"required","overflow":"diagnose","role":"table"}},"constraints":{"connectors":"none","overlap":"diagnose"}}

def test_layout_manifest_is_deterministic_and_reports_unavailable_source():
    p=profile(); a=resolve_layout_profile(p,{"table"}); b=resolve_layout_profile(p,{"table"})
    assert a==b and not a.diagnostics
    assert resolve_layout_profile(p,set()).diagnostics == ("E_LAYOUT_SOURCE_UNAVAILABLE:table",)

def test_solver_uses_declared_split_tracks():
    p=profile(); p["regions"]=[{"id":"main","layout":"split","tracks":["2fr","3fr"]}]; p["slots"]={"table":{"region":"main","source":"table","priority":"required","overflow":"diagnose","role":"table"},"timeline":{"region":"main","source":"timeline","priority":"required","overflow":"diagnose","role":"timeline"}}
    slots=solve_layout(p,resolve_layout_profile(p,{"table","timeline"}))
    assert abs(slots["table"].width * 3 - slots["timeline"].width * 2) <= 1

def test_human_and_ai_preset_share_validated_closure():
    resources={"view":{},"style":{},"theme":{},"layout":profile()}
    assert validate_designer_preset(resources,{"table"})["layoutManifest"].profile_id == "x"
    resources["layout"]["code"]="bad"
    with pytest.raises(ValueError, match="E_PRESET_EXECUTABLE_CONTENT"): validate_designer_preset(resources,{"table"})
