"""
Server-side role enforcement.

(a) One patient cannot see or cancel another patient's appointment, even with a direct
    API call — asserts 403 with NOT_YOUR_APPOINTMENT (expanded per analyze-report C1).
(b) Doctor-A's GET /appointments does not return doctor-B's rows.
Validates User Story 4 and the doctor-side of Principle III.
"""

from __future__ import annotations

from datetime import datetime

from tests.conftest import make_appointment


def test_patient_cannot_see_other_patient_appointments(
    client, session, seed, patient_token, other_patient_token
):
    # P02 has a booking; P01 lists their own appointments and must not see it.
    make_appointment(session, start=datetime(2026, 11, 4, 10, 0), patient_id="P02", doctor_id="D1")
    resp = client.get("/appointments", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 200
    assert all(a["patient"]["id"] == "P01" for a in resp.json())


def test_patient_cannot_cancel_other_patient_appointment(
    client, session, seed, patient_token
):
    # Create a booking owned by P02.
    appt = make_appointment(
        session, start=datetime(2026, 11, 4, 10, 0), patient_id="P02", doctor_id="D1"
    )
    resp = client.post(
        f"/appointments/{appt.id}/cancel",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "NOT_YOUR_APPOINTMENT"
    assert body["message"]


def test_doctor_cannot_see_other_doctors_appointments(
    client, session, seed, doctor_d1_token, doctor_d2_token
):
    # D1 has a Wed 10:00 booking; D2 has a Mon 10:00 Glaucoma booking.
    make_appointment(
        session, start=datetime(2026, 11, 4, 10, 0), patient_id="P01", doctor_id="D1"
    )
    make_appointment(
        session,
        start=datetime(2026, 11, 2, 15, 0),
        patient_id="P02",
        doctor_id="D2",
        speciality="Glaucoma",
    )

    resp1 = client.get("/appointments", headers={"Authorization": f"Bearer {doctor_d1_token}"})
    assert resp1.status_code == 200
    assert all(a["doctor"]["id"] == "D1" for a in resp1.json())

    resp2 = client.get("/appointments", headers={"Authorization": f"Bearer {doctor_d2_token}"})
    assert resp2.status_code == 200
    assert all(a["doctor"]["id"] == "D2" for a in resp2.json())
