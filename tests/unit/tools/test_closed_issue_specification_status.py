"""Closed issue references in normative specs cannot remain implementation-pending."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "docs/reviews/closed-issue-specification-ledger.md"


def _closed_issue_ids(ledger: str) -> frozenset[str]:
    return frozenset(re.findall(r"^\|\s*#?(\d+)\s*\|\s*closed\s*\|", ledger,
                                flags=re.IGNORECASE | re.MULTILINE))


def _stale_paragraphs(document: str, closed: frozenset[str]) -> list[str]:
    stale = []
    for paragraph in re.split(r"\n\s*\n", document):
        normalized = " ".join(paragraph.split()).lower()
        named = set(re.findall(r"(?<!\w)#(\d+)\b", normalized))
        if named & closed and re.search(r"\bimplementation\s+pending\b", normalized):
            stale.append(normalized)
    return stale


def test_normative_specs_have_no_pending_markers_for_closed_issues():
    closed = _closed_issue_ids(LEDGER.read_text(encoding="utf-8"))
    documents = [*sorted((ROOT / "docs/specification").rglob("*.md")),
                 *sorted((ROOT / "docs/decisions").rglob("*.md"))]
    stale = [(path.relative_to(ROOT).as_posix(), paragraph)
             for path in documents
             for paragraph in _stale_paragraphs(path.read_text(encoding="utf-8"), closed)]
    assert not stale, stale


def test_closed_marker_is_found_across_wrapped_lines_but_not_across_paragraphs():
    closed = frozenset({"332"})
    assert _stale_paragraphs("Design for #332 remains\nimplementation pending.", closed)
    assert not _stale_paragraphs("#332 is closed.\n\nImplementation pending elsewhere.", closed)


def test_open_issue_pending_marker_is_allowed():
    assert not _stale_paragraphs("Design for #999 is implementation pending.",
                                 frozenset({"332"}))
