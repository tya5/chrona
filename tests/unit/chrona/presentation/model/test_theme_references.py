"""Theme number-token references and simple expressions resolve once, at load (#1151). Synthetic input only."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.core.identity import content_identity
from chrona.presentation.model.closure import ClosureError, _load_draft_source
from chrona.presentation.model.theme_inheritance import resolve_draft_theme
from chrona.presentation.model.theme_references import ThemeReferenceError, resolve_references, uses_references
from chrona.presentation.model.theme_role_consumers import unread_roles
from chrona.resources import default_preset_root


def _theme(**tokens) -> dict:
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "t",
            "body": {"values": {name: {"type": "number", "value": value} for name, value in tokens.items()},
                     "roles": {"title": {"fontSize": "base"}}, "colorBindings": {"title.fill": "text"}}}


def _values(theme: dict) -> dict:
    return {name: entry["value"] for name, entry in theme["body"]["values"].items()}


def _resolved(**tokens) -> dict:
    return _values(resolve_references(_theme(**tokens)))


def _fails(theme: dict) -> ThemeReferenceError:
    with pytest.raises(ThemeReferenceError) as error:
        resolve_references(theme)
    return error.value


def test_a_theme_without_references_is_returned_unchanged():
    theme = _theme(base=12, other=11.5)
    assert not uses_references(theme)
    assert resolve_references(theme) is theme


def test_an_alias_resolves_to_its_target_with_the_targets_own_number_form():
    assert _resolved(base=14, alias={"ref": "base"}, quoted={"ref": "{base}"}, half=11.5, again={"ref": "half"}, whole=14.0,
                     whole_alias={"ref": "whole"}) == {
        "base": 14, "alias": 14, "quoted": 14, "half": 11.5, "again": 11.5, "whole": 14.0, "whole_alias": 14.0}
    assert type(_resolved(base=14, alias={"ref": "base"})["alias"]) is int


def test_changing_a_base_token_changes_every_alias_and_chains_follow():
    for base in (14, 20):
        values = _resolved(**{"spacing.m": base, "spacing.l": {"expr": "2 * {spacing.m}"},
                              "table-column-gutter": {"ref": "spacing.m"}, "deep": {"ref": "table-column-gutter"}})
        assert values == {"spacing.m": base, "spacing.l": 2 * base, "table-column-gutter": base, "deep": base}


@pytest.mark.parametrize("text, expected", [
    ("0.1 + 0.2", 0.3), ("{a} * 2", 25), ("{a} + {b} * 2", 16.5), ("({a} + {b}) * 2", 29),
    ("-{b} + 1", -1), ("--{b}", 2), ("{a} / 4", 3.125), ("1 / 3", 0.3333333333333333), ("{a} - {a}", 0),
    ("7 / 2 * 2", 7), ("{a}*{b}", 25), ("1.10 * 3", 3.3), ("{a} / 8 + 1", 2.5625),
])
def test_an_expression_evaluates_exactly_with_the_decimal_rules_of_theme_numbers(text, expected):
    result = _resolved(a=12.5, b=2, x={"expr": text})["x"]
    assert result == expected and type(result) is type(expected)


def test_a_float_token_enters_an_expression_as_its_decimal_text_like_every_theme_number():
    assert _resolved(a=0.1, b=0.2, x={"expr": "{a} + {b}"}, y={"expr": "{a} * 3"})["x"] == 0.3
    assert _resolved(a=0.1, y={"expr": "{a} * 3"})["y"] == 0.3


def test_expression_results_are_independent_of_declaration_order():
    forward = _resolved(a=3, b={"expr": "{a} + 1"}, c={"expr": "{b} * {a}"})
    backward = _resolved(c={"expr": "{b} * {a}"}, b={"expr": "{a} + 1"}, a=3)
    assert forward == {"a": 3, "b": 4, "c": 12} and backward == {"c": 12, "b": 4, "a": 3}


def test_a_cycle_fails_at_the_pointer_of_the_token_that_starts_it():
    error = _fails(_theme(a={"ref": "b"}, b={"expr": "{c} + 1"}, c={"ref": "a"}))
    assert (error.code, error.pointer) == ("E_THEME_REF_CYCLE", "/body/values/a/value")
    assert "a -> b -> c -> a" in error.detail
    error = _fails(_theme(x={"expr": "{x} * 2"}))
    assert (error.code, error.pointer) == ("E_THEME_REF_CYCLE", "/body/values/x/value")


def test_an_unknown_reference_fails_at_the_referring_expression():
    error = _fails(_theme(a=1, b={"expr": "{a} + {missing}"}))
    assert (error.code, error.pointer) == ("E_THEME_REF_UNKNOWN", "/body/values/b/value/expr")
    assert "'missing'" in error.detail
    assert _fails(_theme(b={"ref": "missing"})).pointer == "/body/values/b/value/ref"


def test_a_non_number_token_cannot_take_part_in_a_reference():
    theme = _theme(a={"ref": "weight"}, plain=1)
    theme["body"]["values"]["weight"] = {"type": "fontWeight", "value": 400}
    error = _fails(theme)
    assert (error.code, error.pointer) == ("E_THEME_REF_TYPE", "/body/values/weight/value")
    theme = _theme(a=1, b={"ref": "a"})
    theme["body"]["values"]["b"]["type"] = "fontWeight"
    assert _fails(theme).code == "E_THEME_REF_TYPE"
    assert _fails(_theme(a="wide", b={"ref": "a"})).code == "E_THEME_REF_TYPE"
    assert _fails(_theme(a=True, b={"ref": "a"})).code == "E_THEME_REF_TYPE"


@pytest.mark.parametrize("text", ["1 +", "(1 + 2", "1 + 2)", "2 ** 3", "max(1, 2)", "1 2", "{a", "{}", "a", "1e3", "", " ", "1 + * 2",
                                  "1px", "(" * 20 + "1" + ")" * 20, "1" + "+1" * 200])
def test_a_malformed_expression_is_a_syntax_error(text):
    error = _fails(_theme(a=1, x={"expr": text}))
    assert (error.code, error.pointer) == ("E_THEME_REF_SYNTAX", "/body/values/x/value/expr")


def test_division_by_zero_and_non_string_sources_are_typed_errors():
    assert _fails(_theme(a=0, x={"expr": "1 / {a}"})).code == "E_THEME_REF_VALUE"
    assert _fails(_theme(x={"expr": 3})).code == "E_THEME_REF_SYNTAX"
    assert _fails(_theme(x={"ref": ""})).code == "E_THEME_REF_SYNTAX"


def test_a_structured_token_value_that_merely_has_a_ref_key_is_not_a_reference():
    theme = _theme(a=1)
    theme["body"]["values"]["p"] = {"type": "pattern", "value": {"kind": "catalog", "ref": "set:name"}}
    assert not uses_references(theme)
    theme["body"]["values"]["q"] = {"type": "pattern", "value": {"ref": "a"}}
    assert _fails(theme).code == "E_THEME_REF_TYPE"


def test_the_input_is_never_mutated():
    theme = _theme(a=2, b={"expr": "{a} * 3"})
    before = deepcopy(theme)
    resolve_references(theme)
    assert theme == before


def test_resolved_values_enter_the_theme_identity(tmp_path: Path):
    def load(theme: dict) -> object:
        path = tmp_path / "theme.yaml"
        path.write_text(yaml.safe_dump(theme, sort_keys=False), encoding="utf-8")
        return _load_draft_source("theme", path)

    plain = _theme(base=14, alias=28)
    referenced = _theme(base=14, alias={"expr": "2 * {base}"})
    referenced_source = load(referenced)
    assert referenced_source.value == plain
    assert referenced_source.identity.content_identity == content_identity(plain)
    assert load(_theme(base=15, alias={"expr": "2 * {base}"})).identity.content_identity != content_identity(plain)
    # The expression text is not part of the identity: a second spelling of the same values has the same identity.
    assert load(_theme(base=14, alias={"expr": "{base} + {base}"})).identity.content_identity == content_identity(plain)


def test_a_theme_with_no_reference_keeps_its_source_byte_identity(tmp_path: Path):
    path = tmp_path / "theme.yaml"
    path.write_text("# a comment\n" + yaml.safe_dump(_theme(base=14, alias=28)), encoding="utf-8")
    source = _load_draft_source("theme", path)
    assert source.identity.content_identity == "sha256:" + sha256(path.read_bytes()).hexdigest()
    assert source.value == yaml.safe_load(path.read_text(encoding="utf-8"))


def test_a_reference_error_reaches_the_closure_as_a_typed_error_at_its_pointer(tmp_path: Path):
    path = tmp_path / "theme.yaml"
    path.write_text(yaml.safe_dump(_theme(a={"ref": "b"}, b={"ref": "a"})), encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        _load_draft_source("theme", path)
    assert (error.value.diagnostic_id, error.value.source_ref) == ("E_THEME_REF_CYCLE", "/body/values/a/value")


def test_a_bundled_theme_rewritten_with_references_resolves_to_the_same_value():
    bundle = Path(str(default_preset_root())) / "bundles/executive-light/theme.yaml"
    original = yaml.safe_load(bundle.read_text(encoding="utf-8"))
    assert not uses_references(original) and resolve_references(original) is original
    rewritten = deepcopy(original)
    values = rewritten["body"]["values"]
    values["axis-lane-month"]["value"] = {"expr": "{axis-lane-quarter} - {axis-cell-gap}"}
    values["axis-cell-gap"]["value"] = {"expr": "{axis-lane-quarter} / 12"}
    assert resolve_references(rewritten) == original
    assert content_identity(resolve_references(rewritten)) == content_identity(original)


def test_references_do_not_hide_role_consumers_from_the_unread_check():
    theme = _theme(base=12, alias={"ref": "base"})
    theme["body"]["roles"]["orphan-role"] = {"fontSize": "alias"}
    resolved = resolve_references(theme)
    documents = [{"typographyRole": "title"}]
    assert unread_roles(resolved["body"], documents) == unread_roles(
        {**theme["body"], "values": {n: {**e, "value": 12} for n, e in theme["body"]["values"].items()}}, documents)
    assert "orphan-role" in unread_roles(resolved["body"], documents)
    assert "orphan-role" not in unread_roles(resolved["body"], documents + [{"textRole": "orphan-role"}])


def _write_base(tmp_path: Path, base: dict) -> bytes:
    source = yaml.safe_dump(base).encode()
    (tmp_path / "base.yaml").write_bytes(source)
    return source


def _derived(base_resolved: dict, source: bytes, **overrides) -> dict:
    return {"version": "chrona/theme/v0.16", "kind": "theme", "id": "t",
            "body": {"extends": {"id": "t", "path": "base.yaml", "sourceContentIdentity": "sha256:" + sha256(source).hexdigest(),
                                 "contentIdentity": content_identity(base_resolved)},
                     "values": {name: {"type": "number", "value": value} for name, value in overrides.items()}}}


def test_a_derived_theme_overrides_a_token_the_base_aliases_and_may_reference_the_base(tmp_path: Path):
    base = _theme(**{"spacing.m": 14, "spacing.l": {"expr": "2 * {spacing.m}"}, "gutter": {"ref": "spacing.m"}, "base": 1})
    resolved_base = resolve_references(base)
    assert _values(resolved_base)["spacing.l"] == 28
    source = _write_base(tmp_path, base)
    # The declared base identity is the resolved base's identity.
    derived = _derived(resolved_base, source, **{"spacing.m": 20, "gutter": {"expr": "{spacing.m} + 1"}})
    path = tmp_path / "derived.yaml"
    path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    effective = resolve_references(resolve_draft_theme(path))
    assert _values(effective) == {"spacing.m": 20, "spacing.l": 40, "gutter": 21, "base": 1}
    source_of_derived = _load_draft_source("theme", path)
    assert source_of_derived.value == effective
    assert source_of_derived.identity.content_identity == content_identity(effective)


def test_a_derived_theme_must_declare_the_resolved_identity_of_a_base_that_uses_references(tmp_path: Path):
    base = _theme(**{"a": 2, "b": {"ref": "a"}, "base": 1})
    source = _write_base(tmp_path, base)
    derived = _derived(base, source, a=3)  # the raw base's identity, not the resolved one
    path = tmp_path / "derived.yaml"
    path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    with pytest.raises(Exception) as error:
        resolve_draft_theme(path)
    assert getattr(error.value, "code", None) == "E_THEME_INHERITANCE_BASE_IDENTITY"


def test_a_derived_theme_reports_a_cycle_through_the_override_at_its_pointer(tmp_path: Path):
    base = _theme(a=1, b={"ref": "a"}, base=1)
    source = _write_base(tmp_path, base)
    derived = _derived(resolve_references(base), source, a={"ref": "b"})
    path = tmp_path / "derived.yaml"
    path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    with pytest.raises(ClosureError) as error:
        _load_draft_source("theme", path)
    assert (error.value.diagnostic_id, error.value.source_ref) == ("E_THEME_REF_CYCLE", "/body/values/a/value")
