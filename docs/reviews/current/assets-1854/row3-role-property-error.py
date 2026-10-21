"""Reproduce #1854 row 3: the refusal for `pattern` on the calendar-closed role (reuses the test fixtures)."""
import tempfile
from pathlib import Path
from tests.integration import test_band_patterns as t
from chrona.usecases.failure_report import report_failure

parts = t._parts()
parts["theme"]["body"]["values"]["band.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": t.DOTS}}
parts["theme"]["body"]["roles"]["calendar-closed"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 11,
                                                      "pattern": "band.pattern"}
try:
    t._render(Path(tempfile.mkdtemp()), parts)
except Exception as caught:
    row = report_failure(caught).diagnostics[0]
    print(row["code"], row["sourceRef"])
    print(row["message"])
