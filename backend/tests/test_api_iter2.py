"""End-to-end API tests for every Iter 2 acceptance scenario.

LLM is mocked everywhere (conftest.py monkey-patches check_red_flags to a
no-flag stub by default; individual tests override it). This file exercises
the four new refusal codes, role-scoped disclosure of reason/doctor_note,
red-flag persistence across booking outcomes, summary role gate + fallback,
Fact fallback, and urgent-case list + idempotent Mark seen.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.llm.red_flag import RedFlagCheckError, RedFlagResult


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


BOOK_BODY = {
    "doctor_id": "D1",
    "speciality": "Cataract",
    "visit_type": "new",
    "start_ts": "2026-11-04T10:00:00",
    "reason": "Routine check for new glasses",
}


# ---- REASON_REQUIRED / REASON_TOO_LONG ----


def test_booking_without_reason_returns_REASON_REQUIRED(client, seed, patient_token):
    body = {**BOOK_BODY, "reason": "   "}
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 400
    j = resp.json()
    assert j["code"] == "REASON_REQUIRED"
    assert j["message"]


def test_booking_without_reason_field_returns_REASON_REQUIRED(client, seed, patient_token):
    body = {k: v for k, v in BOOK_BODY.items() if k != "reason"}
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 400
    assert resp.json()["code"] == "REASON_REQUIRED"


def test_booking_with_over_300_char_reason_returns_REASON_TOO_LONG(
    client, seed, patient_token
):
    body = {**BOOK_BODY, "reason": "x" * 301}
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 400
    assert resp.json()["code"] == "REASON_TOO_LONG"


# ---- Happy path with reason persists and is role-scoped ----


def test_happy_booking_returns_reason_to_the_patient(client, seed, patient_token):
    resp = client.post("/appointments", json=BOOK_BODY, headers=_auth(patient_token))
    assert resp.status_code == 201, resp.text
    appt = resp.json()
    assert appt["reason"] == BOOK_BODY["reason"]
    # The patient does NOT see doctor_note (clinical content).
    assert appt["doctor_note"] is None
    assert appt["urgent"] is False
    assert appt["red_flag"] is None


def test_other_patient_cannot_read_reason(client, seed, patient_token, other_patient_token):
    client.post("/appointments", json=BOOK_BODY, headers=_auth(patient_token))
    # Other patient's /appointments scope hides P01's rows entirely.
    rows = client.get("/appointments", headers=_auth(other_patient_token)).json()
    assert rows == []


def test_doctor_sees_reason_on_their_own_appointments(client, seed, patient_token, doctor_d1_token):
    client.post("/appointments", json=BOOK_BODY, headers=_auth(patient_token))
    rows = client.get("/appointments", headers=_auth(doctor_d1_token)).json()
    assert len(rows) == 1
    assert rows[0]["reason"] == BOOK_BODY["reason"]


def test_staff_sees_reason_on_everyone(client, seed, patient_token, staff_token):
    client.post("/appointments", json=BOOK_BODY, headers=_auth(patient_token))
    rows = client.get("/appointments", headers=_auth(staff_token)).json()
    assert len(rows) == 1
    assert rows[0]["reason"] == BOOK_BODY["reason"]


# ---- Red-flag path: flagged booking creates an UrgentCase ----


@pytest.fixture
def _red_flag_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers import appointments as mod

    def _yes(_reason: str) -> RedFlagResult:
        return RedFlagResult(
            red_flag=True,
            category="sudden_vision_loss",
            why="Patient reports sudden vision loss.",
        )

    monkeypatch.setattr(mod, "check_red_flags", _yes)


def test_red_flag_booking_persists_urgent_case_and_still_books_when_rules_allow(
    client, seed, patient_token, staff_token, _red_flag_yes
):
    body = {**BOOK_BODY, "reason": "I suddenly cannot see from my left eye"}
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 201
    appt = resp.json()
    assert appt["urgent"] is True
    assert appt["red_flag"]["category"] == "sudden_vision_loss"
    assert "staff have been notified" in appt["red_flag"]["emergency_message"]

    # Urgent case visible to staff.
    urgent = client.get("/urgent-cases", headers=_auth(staff_token)).json()
    assert len(urgent["cases"]) == 1
    assert urgent["cases"][0]["category"] == "sudden_vision_loss"
    assert urgent["cases"][0]["appointment_id"] == appt["id"]


def test_red_flag_persists_even_when_rules_refuse(
    client, seed, patient_token, staff_token, _red_flag_yes
):
    # Dr. Rao Thursday AM — SURGERY_SESSION.
    body = {
        **BOOK_BODY,
        "start_ts": "2026-11-05T10:00:00",  # Thursday
        "reason": "I suddenly cannot see from my left eye",
    }
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 409
    j = resp.json()
    assert j["code"] == "SURGERY_SESSION"
    # Emergency flag still rides along on the refusal payload.
    assert j["red_flag"]["category"] == "sudden_vision_loss"

    # UrgentCase still exists for staff to triage.
    urgent = client.get("/urgent-cases", headers=_auth(staff_token)).json()
    assert len(urgent["cases"]) == 1
    assert urgent["cases"][0]["appointment_id"] is None  # no booking was created


# ---- Red-flag fail-closed ----


def test_red_flag_check_failure_refuses_booking(client, seed, patient_token, monkeypatch):
    from app.routers import appointments as mod

    def _boom(_r):
        raise RedFlagCheckError("stub timeout")

    monkeypatch.setattr(mod, "check_red_flags", _boom)
    resp = client.post("/appointments", json=BOOK_BODY, headers=_auth(patient_token))
    assert resp.status_code == 503
    assert resp.json()["code"] == "RED_FLAG_CHECK_UNAVAILABLE"


# ---- NOTE_REQUIRED on complete ----


def test_complete_requires_a_doctor_note(client, session, seed, doctor_d1_token):
    from datetime import datetime
    from tests.conftest import make_appointment

    appt = make_appointment(
        session, start=datetime(2026, 11, 2, 9, 0), patient_id="P01", doctor_id="D1"
    )
    resp = client.post(
        f"/appointments/{appt.id}/complete",
        json={"doctor_note": "   "},
        headers=_auth(doctor_d1_token),
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "NOTE_REQUIRED"

    # With a note, it completes.
    ok = client.post(
        f"/appointments/{appt.id}/complete",
        json={"doctor_note": "VA 6/9 OD. Review 3 months."},
        headers=_auth(doctor_d1_token),
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "completed"


# ---- Urgent-cases list ordering and Mark seen idempotence ----


def test_urgent_cases_requires_staff(client, seed, patient_token):
    resp = client.get("/urgent-cases", headers=_auth(patient_token))
    assert resp.status_code == 403


def test_mark_urgent_seen_is_idempotent(
    client, seed, patient_token, staff_token, _red_flag_yes
):
    body = {**BOOK_BODY, "reason": "I suddenly cannot see from my left eye"}
    client.post("/appointments", json=body, headers=_auth(patient_token))
    case_id = client.get("/urgent-cases", headers=_auth(staff_token)).json()["cases"][0]["id"]

    r1 = client.post(f"/urgent-cases/{case_id}/seen", headers=_auth(staff_token)).json()
    r2 = client.post(f"/urgent-cases/{case_id}/seen", headers=_auth(staff_token)).json()
    assert r1["seen_at"] == r2["seen_at"]

    # Default list hides seen cases.
    assert client.get("/urgent-cases", headers=_auth(staff_token)).json()["cases"] == []
    # include_seen=true brings it back.
    seen_too = client.get(
        "/urgent-cases?include_seen=true", headers=_auth(staff_token)
    ).json()
    assert len(seen_too["cases"]) == 1


# ---- Fact of the Day fallback ----


def test_fact_of_the_day_returns_caveat_and_fact(client, monkeypatch):
    from app.routers import facts as mod

    monkeypatch.setattr(mod, "generate_fact", lambda prev: "Blinking helps rest the eyes.")
    resp = client.get("/fact-of-the-day")
    assert resp.status_code == 200
    j = resp.json()
    assert j["fact"] == "Blinking helps rest the eyes."
    assert j["caveat"] == "General information, not medical advice"


def test_fact_of_the_day_falls_back_on_llm_error(client, monkeypatch):
    from app.llm.fact import FactUnavailable
    from app.routers import facts as mod

    def _boom(_prev):
        raise FactUnavailable("stub")

    monkeypatch.setattr(mod, "generate_fact", _boom)
    resp = client.get("/fact-of-the-day")
    assert resp.status_code == 200
    j = resp.json()
    assert "20 feet" in j["fact"]  # the canonical fallback text
    assert j["caveat"]


# ---- Doctor summary role gate + fallback ----


def test_summary_is_doctor_only(client, seed, patient_token, staff_token):
    for token in (patient_token, staff_token):
        resp = client.get("/doctor/patients/P01/summary", headers=_auth(token))
        assert resp.status_code == 403
        assert resp.json()["code"] == "NOT_YOUR_APPOINTMENT"


def test_summary_returns_fallback_when_llm_fails(
    client, seed, doctor_d1_token, monkeypatch
):
    from app.llm.summary import SummaryUnavailable
    from app.routers import doctor_views as mod

    def _boom(**_kw):
        raise SummaryUnavailable("stub")

    monkeypatch.setattr(mod, "summarize_patient", _boom)
    resp = client.get(
        "/doctor/patients/P01/summary", headers=_auth(doctor_d1_token)
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["summary"] == "Summary unavailable. See the notes below."
    # Profile + past_visits always present, even on fallback.
    assert "profile" in j
    assert "past_visits" in j


def test_summary_includes_profile_and_past_notes(
    client, session, seed, doctor_d1_token, monkeypatch
):
    from datetime import datetime
    from app.models import PatientProfile
    from app.routers import doctor_views as mod
    from tests.conftest import make_appointment

    session.add(
        PatientProfile(
            patient_id="P01",
            general_health="Type 2 diabetes",
            allergies="None recorded",
        )
    )
    # Completed visit with D1 (same doctor) so it lands in past_visits.
    make_appointment(
        session,
        start=datetime(2026, 1, 15, 10, 0),
        patient_id="P01",
        doctor_id="D1",
        status="completed",
    )
    session.commit()

    captured: dict = {}

    def _spy(**kw):
        captured.update(kw)
        return "stub summary"

    monkeypatch.setattr(mod, "summarize_patient", _spy)
    resp = client.get(
        "/doctor/patients/P01/summary", headers=_auth(doctor_d1_token)
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["summary"] == "stub summary"
    assert j["profile"]["general_health"] == "Type 2 diabetes"
    assert j["profile"]["year_of_birth"] == 1958  # set in conftest seed
    assert any(v["doctor_name"] == "Dr. Anand Rao" for v in j["past_visits"])

    # The chain saw the recorded data (not something we invented).
    assert captured["age"] is not None
    assert captured["general_health"] == "Type 2 diabetes"
    assert captured["allergies"] == "None recorded"
    assert any(v["doctor_name"] == "Dr. Anand Rao" for v in captured["past_visits"])
