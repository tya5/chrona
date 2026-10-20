"""Built-in wording tables, the resolver precedence and the `{wording: key}` reference end to end (#1724 P4a)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re

import pytest

from chrona.presentation.model.wording_tables import (
    WordingResolver, validate_wording_catalog, wording_catalog, wording_keys, wording_resolver,
)
from chrona.presentation.review.profile_connections import ProfileConnectionError, resolve_profile_connections
from chrona.resources import safe_load, schema_validator, wording_tables_resource
from tests.support import synthetic_review as sr


# Acceptance 2 of #1724: this is the list of every built-in wording key. A new key is a row here and an entry in
# every locale; `--locale ja-JP` then has no English built-in wording for it.
BUILT_IN_WORDING_KEYS = (
    "column.task", "column.plan", "column.lane", "column.items",
    "marker.today", "marker.asOf", "marker.baselineNew", "marker.baselineRemoved",
    "legend.planned", "legend.actual", "legend.milestone", "legend.dependency", "legend.asOf",
    "legend.calendar-closed", "legend.critical-edge", "legend.forecast", "legend.progressFill",
    "legend.actual-ahead", "legend.actual-on-track", "legend.actual-behind",
    "legend.snapshot", "legend.deadlineMark",
    "missing.unknown", "missing.inProgress",
    "legend.planned-plain", "legend.baseline", "legend.current-plan", "legend.gate", "legend.holiday",
    "column.owner", "column.number", "column.phase", "column.finishDelta",
    "column.finishDeltaPlan", "column.finishDeltaBaseline", "summary.days",
    "legend.plan", "legend.missing-actual", "legend.missing-actual-in-progress", "legend.in-the-wings",
    "legend.calendar-exception", "legend.period", "legend.depends-on", "legend.other", "column.no",
    "delta.unit.calendarDay", "delta.unit.workingDay",
)
LOCALES = ("en-US", "ja-JP")


def test_the_table_holds_exactly_the_listed_keys_and_every_locale_has_every_key():
    document = safe_load(wording_tables_resource().read_bytes())
    schema_validator("wording-tables-v0.1.schema.yaml").validate(document)
    assert wording_keys() == BUILT_IN_WORDING_KEYS
    catalog = wording_catalog()
    assert tuple(catalog) == LOCALES
    for locale in LOCALES:
        assert tuple(catalog[locale]) == BUILT_IN_WORDING_KEYS, locale
        assert all(isinstance(text, str) and text.strip() for text in catalog[locale].values()), locale


def test_no_japanese_entry_repeats_the_english_text_and_the_closed_day_is_not_weekend():
    catalog = wording_catalog()
    for key in BUILT_IN_WORDING_KEYS:
        assert catalog["ja-JP"][key] != catalog["en-US"][key], key
        assert re.search(r"[぀-ヿ一-鿿]", catalog["ja-JP"][key]), key
    assert catalog["en-US"]["legend.calendar-closed"] == "Non-working day"
    assert catalog["ja-JP"]["legend.calendar-closed"] == "休業日"
    assert all("weekend" not in text.lower() for text in catalog["en-US"].values())


def test_the_en_us_entries_are_the_literals_the_code_and_presets_used_before():
    table = wording_catalog()["en-US"]
    assert (table["column.task"], table["column.plan"], table["marker.today"], table["legend.critical-edge"],
            table["missing.unknown"], table["missing.inProgress"]) == (
        "Task", "Plan", "TODAY", "Critical dependency", "unknown", "in progress")
    # P4c: the literals Layout and the lane table held before the table owned them.
    assert (table["column.lane"], table["column.items"], table["legend.progressFill"], table["legend.actual-ahead"],
            table["legend.actual-on-track"], table["legend.actual-behind"]) == (
        "Lane", "Items", "Progress", "Ahead", "On track", "Behind")
    ja = wording_catalog()["ja-JP"]
    assert (ja["column.lane"], ja["column.items"], ja["legend.progressFill"], ja["legend.actual-ahead"],
            ja["legend.actual-on-track"], ja["legend.actual-behind"]) == (
        "レーン", "件数", "進捗", "前倒し", "予定どおり", "遅れ")


@pytest.mark.parametrize("mutation", [
    lambda value: value["tables"]["ja-JP"].pop("column.task"),
    lambda value: value["tables"]["ja-JP"].update({"column.extra": "x"}),
    lambda value: value["tables"]["en-US"].update({"column.task": " "}),
    lambda value: value["tables"].pop("ja-JP"),
    lambda value: value.update({"version": "chrona/wording-tables/v9"}),
])
def test_an_incomplete_or_malformed_catalog_is_rejected(mutation):
    document = deepcopy(safe_load(wording_tables_resource().read_bytes()))
    mutation(document)
    with pytest.raises(ValueError, match="E_WORDING_TABLE_RESOURCE"):
        validate_wording_catalog(document)


def test_the_resolver_orders_table_then_keys_then_the_legend_entry():
    plain = WordingResolver("ja-JP")
    assert plain.text("column.task") == "タスク"
    assert WordingResolver("fr-FR").text("column.task") == "Task"  # an unsupported locale reads the en-US entry
    keyed = wording_resolver("ja-JP", {"keys": {"legend.planned": "計画"}, "legend": {"planned": "予定"}})
    assert keyed.text("legend.planned") == "計画"                    # level 3 over the table
    assert keyed.legend_text("planned") == "予定"                    # level 4 over level 3
    assert keyed.legend_text("actual") == "実績"                     # untouched roles keep the table text
    assert wording_resolver("en-US", {"keys": {"legend.planned": "Plan"}}).legend_text("planned", "Authored") == "Plan"
    assert plain.legend_text("planned", "Authored") == "Authored"   # level 2 over the table
    assert plain.resolve({"wording": "marker.today"}) == "本日"
    assert plain.resolve("TODAY") == "TODAY"                         # an authored literal is never translated
    with pytest.raises(ValueError, match="E_WORDING_KEY_UNKNOWN"):
        plain.text("column.nope")


def test_the_closed_day_legend_key_carries_critical_edge_through_wording_legend_unchanged():
    # Dev A (#1727): `wording.legend.critical-edge` stays the most specific override; the default is the table entry.
    assert wording_resolver("en-US", None).legend_text("critical-edge") == "Critical dependency"
    assert wording_resolver("en-US", {"legend": {"critical-edge": "Long pole"}}).legend_text("critical-edge") == "Long pole"
    assert wording_resolver("ja-JP", None).legend_text("critical-edge") == "クリティカルな依存関係"
    assert wording_resolver("en-US", {"keys": {"legend.critical-edge": "Gate path"}}).legend_text("critical-edge") == "Gate path"


def test_an_unknown_wording_key_is_a_view_wording_error_at_its_pointer():
    from tests.unit.chrona.presentation.review.test_profile_connections import _view
    with pytest.raises(ProfileConnectionError) as raised:
        resolve_profile_connections(_view(wording={"keys": {"column.nope": "x"}}), None, None, project_object_ids=frozenset())
    assert (raised.value.code, raised.value.source_ref) == ("E_VIEW_WORDING_UNKNOWN", "/body/wording/keys/column.nope")


# --- the schema ----------------------------------------------------------------------------------------------

def test_the_view_schema_accepts_a_reference_and_a_literal_and_rejects_an_unknown_key():
    parts = sr.bundle("editorial")
    view = parts["view"]
    validator = schema_validator("view-v0.28.schema.yaml")
    validator.validate(view)
    changed = deepcopy(view)
    body = changed["body"]
    body["tableColumns"][0]["header"] = {"wording": "column.task"}
    body["tableColumns"][1]["header"] = "Owner name"
    body["markers"][0]["label"] = {"wording": "marker.today"}
    body["wording"] = {"keys": {"legend.calendar-closed": "Holiday"}}
    validator.validate(changed)
    for mutate in (lambda b: b["tableColumns"][0].update({"header": {"wording": "column.nope"}}),
                   lambda b: b["tableColumns"][0].update({"header": ""}),
                   lambda b: b["markers"][0].update({"label": {"wording": "column.nope"}}),
                   lambda b: b["wording"].update({"keys": {"": "x"}})):
        broken = deepcopy(changed)
        mutate(broken["body"])
        assert list(validator.iter_errors(broken))


def test_the_detail_schema_accepts_a_reference_label_and_rejects_an_unknown_key():
    validator = schema_validator("review-detail-profile-v0.1.schema.yaml")
    ok = {"version": "chrona/review-detail-profile/v0.1", "id": "d",
          "body": {"legend": [{"role": "planned", "label": {"wording": "legend.planned"}}, {"role": "x", "label": "Literal"}]}}
    validator.validate(ok)
    bad = deepcopy(ok)
    bad["body"]["legend"][0]["label"] = {"wording": "legend.nope"}
    assert list(validator.iter_errors(bad))


# --- a synthetic preset that references the keys, rendered per locale ---------------------------------------

def _texts(review) -> list[str]:
    content = review.artifact.content
    svg = content.decode("utf-8") if isinstance(content, bytes) else content
    return [re.sub(r"<[^>]+>", "", body) for body in re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S)]


def _referencing_parts(*, with_keys: dict[str, str] | None = None, legend_override: dict[str, str] | None = None):
    parts = sr.bundle("editorial")
    body = parts["view"]["body"]
    body["tableColumns"][0]["header"] = {"wording": "column.task"}
    body["tableColumns"].append({
        "id": "Plan", "header": {"wording": "column.plan"}, "source": {"facet": "planned"}, "format": "dateRange",
        "endDisplay": "inclusive", "missing": "em-dash", "align": "start", "width": "content",
        "headerOrientation": "horizontal"})
    body["markers"][0]["label"] = {"wording": "marker.today"}
    if with_keys or legend_override:
        body["wording"] = {**({"keys": with_keys} if with_keys else {}), **({"legend": legend_override} if legend_override else {})}
    return parts


_DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "synthetic-detail", "body": {"legend": [
    {"role": "planned", "label": {"wording": "legend.planned"}},
    {"role": "asOf", "label": {"wording": "legend.asOf"}},
    {"role": "calendar-closed", "label": {"wording": "legend.calendar-closed"}},
]}}
_ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-actual",
           "body": {"asOf": "2026-01-12", "observations": []}}


def _render(tmp_path, locale, **kwargs):
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 1, 5), 20), "b": sr.span("b", date(2026, 1, 19), 20)}))
    return _texts(sr.render(tmp_path, source, presentation=_referencing_parts(**kwargs), detail=_DETAIL,
                            actual=_ACTUAL, locale=locale))


def test_a_preset_that_references_keys_renders_english_under_en_us(tmp_path):
    texts = _render(tmp_path, "en-US")
    assert {"Task", "Plan", "TODAY", "TASK DURATION", "NON-WORKING DAY"} <= set(text.strip() for text in texts), texts


def test_the_same_preset_renders_task_plan_today_and_legend_in_japanese_under_ja_jp(tmp_path):
    texts = [text.strip() for text in _render(tmp_path, "ja-JP")]
    for expected in ("タスク", "計画", "本日", "計画期間", "休業日"):
        assert expected in texts, (expected, texts)
    for english in ("Task", "Plan", "TODAY", "Task duration", "Non-working day", "Weekend"):
        assert not any(english.lower() == text.lower() for text in texts), (english, texts)


def _upper(texts):
    return [text.strip().upper() for text in texts]


def test_view_keys_override_the_table_and_wording_legend_overrides_both(tmp_path):
    (tmp_path / "keys").mkdir()
    keyed = _upper(_render(tmp_path / "keys", "ja-JP", with_keys={"column.task": "作業", "legend.calendar-closed": "祝日"}))
    assert "作業" in keyed and "祝日" in keyed and "休業日" not in keyed
    (tmp_path / "both").mkdir()
    both = _upper(_render(tmp_path / "both", "ja-JP", with_keys={"legend.calendar-closed": "祝日"},
                          legend_override={"calendar-closed": "休み"}))
    assert "休み" in both and "祝日" not in both


def test_an_authored_literal_stays_untranslated_and_a_key_override_replaces_it_on_its_legend_role(tmp_path):
    parts = _referencing_parts()
    parts["view"]["body"]["markers"][0]["label"] = "TODAY"
    detail = {**_DETAIL, "body": {"legend": [{"role": "planned", "label": "Planned"},
                                              {"role": "calendar-closed", "label": "Weekend"}]}}
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 1, 5), 20)}))
    texts = _upper(_texts(sr.render(tmp_path, source, presentation=parts, detail=detail, actual=_ACTUAL, locale="ja-JP")))
    assert {"PLANNED", "WEEKEND", "TODAY"} <= set(texts)
    (tmp_path / "keyed").mkdir()
    parts["view"]["body"]["wording"] = {"keys": {"legend.calendar-closed": "Holiday"}}
    texts = _upper(_texts(sr.render(tmp_path / "keyed", source, presentation=parts, detail=detail, actual=_ACTUAL, locale="ja-JP")))
    assert {"PLANNED", "HOLIDAY"} <= set(texts) and "WEEKEND" not in texts


# --- built-in wording that was a literal in code ------------------------------------------------------------

def test_missing_words_come_from_the_caller_and_default_to_the_english_literals():
    from chrona.presentation.model.surface_content import display_value
    assert display_value(None, "unknown") == "unknown" and display_value(None, "in-progress") == "in progress"
    words = wording_resolver("ja-JP", None).missing_words()
    assert (display_value(None, "unknown", missing_words=words), display_value(None, "in-progress", missing_words=words),
            display_value(None, "em-dash", missing_words=words), display_value(None, {"text": "TBD"}, missing_words=words)) == (
        "不明", "進行中", "—", "TBD")


def test_a_declared_progress_entry_resolves_its_reference_and_layout_defaults_follow_the_locale():
    # A Detail entry that declares `progressFill` resolves like any other legend entry; the undeclared Progress key
    # and the Actual qualifiers are Layout defaults that now come from the same table (#1724 P4c).
    from chrona.presentation.contracts.resources import LegendEntry
    from chrona.presentation.review.profile_connections import _legend_label
    entry = LegendEntry("progressFill", {"wording": "legend.progressFill"})
    assert _legend_label(entry, wording_resolver("ja-JP", None), frozenset(wording_keys())) == "進捗"
    assert _legend_label(entry, wording_resolver("ja-JP", {"legend": {"progressFill": "完了"}}), frozenset(wording_keys())) == "完了"
    for role, ja_text in (("actual-ahead", "前倒し"), ("actual-on-track", "予定どおり"), ("actual-behind", "遅れ")):
        assert wording_resolver("ja-JP", None).legend_text(role) == ja_text
        assert wording_resolver("ja-JP", {"legend": {role: "X"}}).legend_text(role) == "X"
        assert wording_resolver("ja-JP", {"keys": {f"legend.{role}": "Y"}}).legend_text(role) == "Y"


# --- P4c follow-up: preset literals as keys, and the two new schema places -----------------------------------

def test_the_keys_that_replace_preset_literals_read_as_the_literal_in_en_us_and_in_japanese_otherwise():
    en, ja = wording_catalog()["en-US"], wording_catalog()["ja-JP"]
    assert {key: en[key] for key in ("legend.planned-plain", "legend.baseline", "legend.current-plan", "legend.gate",
                                      "legend.holiday", "column.owner", "column.number", "column.phase",
                                      "column.finishDelta", "column.finishDeltaPlan",
                                      "column.finishDeltaBaseline", "summary.days")} == {
        "legend.planned-plain": "Planned", "legend.baseline": "baseline", "legend.current-plan": "current plan",
        "legend.gate": "gate", "legend.holiday": "holiday", "column.owner": "Owner", "column.number": "No.",
        "column.phase": "Phase", "column.finishDelta": "Δ finish",
        "column.finishDeltaPlan": "Δ vs plan", "column.finishDeltaBaseline": "Δ vs baseline",
        "summary.days": "DAYS"}
    assert en["legend.planned-plain"] != en["legend.planned"]  # `Planned` is not `Task duration`
    assert all(re.search(r"[぀-ヿ一-鿿]", ja[key]) for key in en)


def test_the_layout_marker_label_and_the_lane_table_header_accept_a_reference_and_reject_an_unknown_key():
    layout = schema_validator("layout-profile-v0.10.schema.yaml")
    probe = deepcopy(sr.bundle("editorial")["layout"])
    probe.setdefault("viewDefaults", {})["markerPresentation"] = {"kind": "asOf", "label": {"wording": "marker.asOf"}}
    assert not list(layout.iter_errors(probe))
    probe["viewDefaults"]["markerPresentation"]["label"] = {"wording": "marker.nope"}
    assert list(layout.iter_errors(probe))
    view = schema_validator("view-v0.28.schema.yaml")
    lane = sr.lane_view(sr.bundle("editorial")["view"])
    lane["body"]["rows"]["laneTable"]["columns"] = [
        {"id": "Task", "source": "label", "header": {"wording": "column.task"}},
        {"id": "Owner", "source": {"field": "owner"}, "header": "Resp."}]
    assert not list(view.iter_errors(lane))
    lane["body"]["rows"]["laneTable"]["columns"][0]["header"] = {"wording": "column.nope"}
    assert list(view.iter_errors(lane))


def _lane_parts():
    parts = sr.bundle("editorial")
    parts["view"] = sr.lane_view(parts["view"])
    parts["view"]["body"]["rows"]["laneTable"]["columns"] = [
        {"id": "Task", "source": "label", "header": {"wording": "column.task"}},
        {"id": "Owner", "source": {"field": "owner"}, "header": {"wording": "column.owner"}},
    ]
    parts["view"]["body"]["rows"]["laneTable"]["count"] = False
    for marker in parts["view"]["body"]["markers"]:
        marker.pop("label", None)
    parts["layout"].setdefault("viewDefaults", {})["markerPresentation"] = {"kind": "asOf", "label": {"wording": "marker.asOf"}}
    return parts


@pytest.mark.parametrize("locale, expected", [("en-US", {"Task", "Owner", "As of"}), ("ja-JP", {"タスク", "担当", "基準日"})])
def test_the_lane_table_header_and_the_layout_marker_label_resolve_per_locale(tmp_path, locale, expected):
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 1, 5), 20)}))
    texts = {text.strip() for text in _texts(sr.render(tmp_path, source, presentation=_lane_parts(), actual=_ACTUAL,
                                                       locale=locale))}
    assert expected <= texts, (expected, texts)
