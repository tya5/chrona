from chrona.layout import resolve_layout_profile

def profile():
    return {"version":"chrona/layout-profile/v0.1","id":"x","canvas":{},"regions":[{"id":"main","layout":"split"}],"slots":{"table":{"region":"main","source":"table","priority":"required","overflow":"diagnose","role":"table"}},"constraints":{"connectors":"none","overlap":"diagnose"}}

def test_layout_manifest_is_deterministic_and_reports_unavailable_source():
    p=profile(); a=resolve_layout_profile(p,{"table"}); b=resolve_layout_profile(p,{"table"})
    assert a==b and not a.diagnostics
    assert resolve_layout_profile(p,set()).diagnostics == ("E_LAYOUT_SOURCE_UNAVAILABLE:table",)
