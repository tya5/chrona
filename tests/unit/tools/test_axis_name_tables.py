from tools.axis_name_tables import render_audit


def test_audit_reports_japanese_full_aliases_and_english_may_coincidence():
    audit = render_audit()
    assert "| `long-month` | `short-month` | 5 |" in audit
    assert "| `long-month` | `short-month` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 |" in audit
    assert "| `numeric-month` | 01 |" in audit
