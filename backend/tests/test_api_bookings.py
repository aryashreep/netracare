"""
End-to-end API: book, list, cancel, rebook same slot.
Every 409 asserted here MUST carry both `code` (one of the 17 canonical codes) and
`message` (non-empty). Enforced via assert_refusal() (analyze-report C2).
"""

from __future__ import annotations

from app.errors import REASON_CODES


def assert_refusal(resp, expected_code: str) -> None:
    assert resp.status_code == 409, resp.text
    body = resp.json()
    assert "code" in body and "message" in body
    assert body["code"] == expected_code
    assert body["code"] in REASON_CODES
    assert body["message"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_happy_path(client, seed, patient_token):
    body = {
        "doctor_id": "D1",
        "speciality": "Cataract",
        "visit_type": "new",
        "start_ts": "2026-11-04T10:00:00",
    }
    resp = client.post("/appointments", json=body, headers=_auth(patient_token))
    assert resp.status_code == 201, resp.text
    appt = resp.json()
    assert appt["status"] == "booked"
    assert appt["end_ts"] == "2026-11-04T10:20:00"

    # Patient sees their own.
    mine = client.get("/appointments", headers=_auth(patient_token)).json()
    assert len(mine) == 1
    assert mine[0]["id"] == appt["id"]


def test_second_patient_cannot_book_same_slot(client, seed, patient_token, other_patient_token):
    body = {
        "doctor_id": "D1",
        "speciality": "Cataract",
        "visit_type": "new",
        "start_ts": "2026-11-04T10:00:00",
    }
    client.post("/appointments", json=body, headers=_auth(patient_token))
    body["speciality"] = "Cataract"
    # P02 tries the exact same slot.
    resp = client.post("/appointments", json=body, headers=_auth(other_patient_token))
    assert_refusal(resp, "DOUBLE_BOOKED")


def test_cancel_and_rebook(client, seed, patient_token, other_patient_token):
    body = {
        "doctor_id": "D1",
        "speciality": "Cataract",
        "visit_type": "new",
        "start_ts": "2026-11-04T10:00:00",
    }
    appt = client.post("/appointments", json=body, headers=_auth(patient_token)).json()

    # Patient cancels (well over 2h out).
    resp = client.post(f"/appointments/{appt['id']}/cancel", headers=_auth(patient_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # Another patient books the same slot.
    resp2 = client.post("/appointments", json=body, headers=_auth(other_patient_token))
    assert resp2.status_code == 201


def test_staff_can_cancel_inside_2h(client, session, seed, staff_token, patient_token):
    # Make a booking at 11:00 same day (1h from the fixed clock at 10:00).
    from tests.conftest import make_appointment
    from datetime import datetime

    appt = make_appointment(
        session, start=datetime(2026, 11, 2, 11, 0), patient_id="P01", doctor_id="D1"
    )

    # Patient cannot cancel.
    resp_p = client.post(f"/appointments/{appt.id}/cancel", headers=_auth(patient_token))
    assert_refusal(resp_p, "INSIDE_2_HOURS")

    # Staff can.
    resp_s = client.post(f"/appointments/{appt.id}/cancel", headers=_auth(staff_token))
    assert resp_s.status_code == 200
    assert resp_s.json()["status"] == "cancelled"
