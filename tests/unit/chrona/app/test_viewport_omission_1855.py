import pytest

from chrona.app.agent_tools import _tool_viewport, tool_specs
from chrona.usecases.failure_report import StableFailure
from chrona.app.cli import _parser


@pytest.mark.parametrize(("command", "target"), [
    (["render", "project.yaml", "--output", "slide.svg"], "render"),
    (["render-workspace", "workspace.yaml", "--output", "slide.svg"], "render-workspace"),
])
def test_cli_keeps_omitted_viewport_as_none_and_documents_profile_default(command, target):
    parser = _parser()
    args = parser.parse_args(command)
    assert args.command == target
    assert args.viewport is None
    action = next(action for action in parser._actions
                  if getattr(action, "choices", None) and target in action.choices)
    child = action.choices[target]
    viewport = next(item for item in child._actions if item.dest == "viewport")
    assert viewport.default is None
    assert "Layout Profile page size" in viewport.help
    assert "1600xauto" in viewport.help


def test_mcp_viewport_is_optional_without_a_schema_default():
    specs = {spec.name: spec for spec in tool_specs()}
    for name in ("render_draft", "render_workspace"):
        property_schema = specs[name].input_schema["properties"]["viewport"]
        assert "default" not in property_schema
    assert _tool_viewport({}) is None
    assert _tool_viewport({"viewport": "1200x700"}) == "1200x700"
    with pytest.raises(StableFailure, match="viewport must match"):
        _tool_viewport({"viewport": None})
