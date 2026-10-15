"""The packaged technical-print lane table carries number, task and owner-initials columns (#1529)."""
from tests.integration import test_packaged_bounded_table as bounded


def test_technical_print_lane_table_columns_and_bold_header(tmp_path):
    parts = bounded._parts("technical-print")
    columns = parts["view"]["body"]["rows"]["laneTable"]["columns"]
    assert [column["id"] for column in columns] == ["No", "Task", "Owner"]
    assert columns[0]["source"] == "rowIndex" and columns[1]["source"] == "label"
    assert columns[2]["source"] == {"field": "owner"} and columns[2]["transform"] == "initials"
    assert parts["theme"]["body"]["roles"]["tableColumnLabel"]["fontWeight"] == "weight.bold"
    rendered = bounded.sr.render(tmp_path, bounded._source(), presentation=parts,
                                 icon_catalogs=bounded._catalogs(tmp_path, "technical-print"))
    text = rendered.artifact.content.decode("utf-8")
    for header in ("No", "Task", "Owner"):
        assert f">{header}</text>" in text
