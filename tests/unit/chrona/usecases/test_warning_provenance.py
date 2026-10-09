"""Explicit Project provenance enriches messages, not warning identities/counts."""
from __future__ import annotations

from types import SimpleNamespace

from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject, PrimitiveProvenance
from chrona.usecases.diagnostic_messages import collapse_warnings
from chrona.usecases.warning_ledger import collect_render_warnings
from chrona.usecases.render_review import _finding_subjects


def test_exact_primitive_join_preserves_all_explicit_subjects_without_guessing():
    first = DiagnosticSubject.project_object("first", "First")
    second = DiagnosticSubject.project_object("second", "Second")
    third = DiagnosticSubject.project_object("third", "Third")
    provenance = (PrimitiveProvenance("opaque", (first,)),
                  PrimitiveProvenance("opaque", (second, first)),
                  PrimitiveProvenance("other", (third,)))
    assert _finding_subjects(("opaque", "other", "opaque"), provenance) == (first, second, third)
    assert _finding_subjects(("planned:first", "/objects/first"), provenance) == ()


def _collect(diagnostics=(), provenance=(), **families):
    options = dict(surface_diagnostics=diagnostics, surface_provenance=provenance,
                   tabular_warnings=(), glyph_warnings=(), fit_warnings=(),
                   perceptibility_warnings=(), scale_collisions=(), attachment_warnings=())
    options.update(families)
    return collect_render_warnings(**options)


def test_owner_pointer_title_preserves_first_occurrence_and_multiplicity():
    diagnostics = ("W_LAYOUT_LABEL_SUPPRESSED:opaque:first", "W_LAYOUT_LABEL_SUPPRESSED:opaque:second")
    subjects = (DiagnosticSubject.project_object("a/~b", "Design: Alpha"),
                DiagnosticSubject.project_object("second", "Other title"))
    plain = _collect(diagnostics)
    enriched = _collect(diagnostics, tuple(DiagnosticProvenance(value, (subject,))
                                         for value, subject in zip(diagnostics, subjects, strict=True)))
    assert tuple(item.identity for item in enriched) == tuple(item.identity for item in plain) == diagnostics
    rows = collapse_warnings(item.payload for item in enriched)
    before = collapse_warnings(item.payload for item in plain)
    assert len(rows) == len(before) == 1
    assert rows[0]["sourceRef"] == "/objects/a~1~0b"
    assert "Design: Alpha" in rows[0]["message"] and "Other title" not in rows[0]["message"]
    assert rows[0]["count"] == before[0]["count"] == 2
    assert rows[0]["occurrences"] == before[0]["occurrences"] == list(diagnostics)
    assert rows[0]["diagnostic"] == before[0]["diagnostic"]


def test_ownerless_warnings_are_not_given_project_ownership():
    row, = _collect(("W_LAYOUT_AXIS_DENSITY:calendar:tier",))
    assert "sourceRef" not in row.payload and "sourceTitle" not in row.payload
    assert "/objects/" not in row.payload["message"]


def test_same_identity_occurrences_keep_their_ordered_explicit_subjects():
    identity = "W_LAYOUT_LABEL_SUPPRESSED:opaque"
    provenance = tuple(DiagnosticProvenance(identity, (DiagnosticSubject.project_object(key, key),))
                       for key in ("first", "second"))
    records = _collect((identity, identity), provenance)
    assert [item.payload["sourceRef"] for item in records] == ["/objects/first", "/objects/second"]
    row, = collapse_warnings(item.payload for item in records)
    assert row["count"] == 2 and row["occurrences"] == [identity]


def test_multi_owner_scene_finding_names_subjects_without_renaming_identity():
    finding = SimpleNamespace(code="W_SCENE_TEXT_INTERSECTION", finding_code="E_SCENE_TEXT_INTERSECTION",
                              scene_path="/root/children/2", primitive_ids=("opaque1", "opaque2"),
                              slot_id="timeline", measured_facts=(), disposition=None, subjects=())
    before, = _collect(perceptibility_warnings=(finding,))
    finding.subjects = (DiagnosticSubject.project_object("x", "First title"),
                        DiagnosticSubject.project_object("y", "Second title"))
    after, = _collect(perceptibility_warnings=(finding,))
    assert before.identity == after.identity
    assert before.payload["diagnostic"] == after.payload["diagnostic"]
    assert after.payload["sourceRef"] == "/objects/x"
    assert "First title" in after.payload["message"] and "Second title" in after.payload["message"]
    assert [item["sourceRef"] for item in after.payload["sourceSubjects"]] == ["/objects/x", "/objects/y"]


def test_unknown_title_keeps_explicit_pointer_not_a_fabricated_title():
    identity = "W_LAYOUT_LABEL_SUPPRESSED:opaque"
    record, = _collect((identity,), (DiagnosticProvenance(identity, (DiagnosticSubject.project_object("known"),)),))
    assert record.payload["sourceRef"] == "/objects/known"
    assert "/objects/known" in record.payload["message"]
    assert "sourceTitle" not in record.payload


def test_fit_payload_pointer_changes_without_changing_existing_raw_identity():
    fit = SimpleNamespace(code="W_LAYOUT_TEXT_ELLIPSIZED", placement_id="opaque", source_ref="original",
                          failure_kind="fit", behaviour="ellipsize", required_inline=30, required_block=10,
                          available_inline=20, available_block=10, subjects=())
    before, = _collect(fit_warnings=(fit,))
    fit.subjects = (DiagnosticSubject.project_object("original", "Visible name"),)
    after, = _collect(fit_warnings=(fit,))
    assert before.identity == after.identity
    assert after.payload["sourceRef"] == "/objects/original" and "Visible name" in after.payload["message"]
    assert "needs 30x10" in after.payload["message"]
