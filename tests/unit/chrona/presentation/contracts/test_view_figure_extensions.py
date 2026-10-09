"""#927: closed schema vocabulary and typed figure ingress agree."""
import pytest

from chrona.core.figures import COUNT_SOURCES, KINDS
from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import SchemaContractError
from chrona.resources import schema_validator
from tests.support import synthetic_review as sr


def _parse(figure):
    value = sr.bundle("control-room-dark")["view"]
    value["body"]["figures"] = [figure]
    return parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value).view


def test_schema_and_core_share_the_closed_kind_and_count_source_sets():
    schema = schema_validator("view-v0.28.schema.yaml").schema
    definitions = schema["$defs"]
    kinds = tuple(definitions[name]["properties"]["kind"]["const"]
                  for name in ("figureDaysUntil", "figureDaysIn", "figureCount"))
    assert kinds == KINDS
    assert tuple(definitions["figureCount"]["properties"]["source"]["enum"]) == COUNT_SOURCES


@pytest.mark.parametrize("source", COUNT_SOURCES)
def test_every_declared_count_source_is_typed_at_ingress(source):
    (figure,) = _parse({"id": "n", "kind": "count", "source": source}).figures
    assert (figure.figure_id, figure.kind, figure.source, figure.scope) == ("n", "count", source, "global")


@pytest.mark.parametrize("extra", [{"source": "anything"}, {"days": "working"},
                                    {"calendar": "c"}, {"to": "asOf"}, {"expression": "1+2"}])
def test_count_figures_have_no_date_or_expression_fallback(extra):
    with pytest.raises(SchemaContractError):
        _parse({"id": "n", "kind": "count", "source": "selected", **extra})
