"""An owner cell shows its whole name in a content-width column, in Latin and in CJK text (#1629).

The packaged technical-print Owner column declares `transform: initials`, which is why it shows one letter. The
column itself is content-width, so with the transform omitted every name fits inside its column. Synthetic Project.
"""
import re
from copy import deepcopy
from datetime import date

import pytest

from tests.integration import test_packaged_bounded_table as bounded
from tests.support import synthetic_review as sr

OWNERS = ("Priya Raman", "佐藤健太郎", "QT Team")


def _full_name_parts():
    parts = deepcopy(bounded._parts("technical-print"))
    owner = next(column for column in parts["view"]["body"]["rows"]["laneTable"]["columns"] if column["id"] == "Owner")
    owner.pop("transform")
    return parts


@pytest.mark.parametrize("owner", OWNERS, ids=["latin", "cjk", "latin-words"])
def test_owner_cell_is_whole_and_inside_the_table(tmp_path, owner):
    source = sr.project({"a": sr.span("a", date(2027, 1, 4), 8, owner=owner, title="Alpha")})
    source["entities"] = {owner: {"type": "team", "title": owner}}
    rendered = sr.render(tmp_path, source, presentation=_full_name_parts(),
                         icon_catalogs=bounded._catalogs(tmp_path, "technical-print"))
    text = rendered.artifact.content.decode("utf-8")
    plain = re.sub(r"<[^>]+>", "", text)  # fallback faces split a run into tspans
    assert owner in plain
    assert "…" not in text
