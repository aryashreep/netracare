"""
Canonical refusal contract. The 21 reason codes below are listed in
docs/conventions.md §2 and are frozen by the constitution — renaming any
of them is a MAJOR constitution amendment.

Iter 1 shipped 17 codes. Iter 2 adds four (REASON_REQUIRED, REASON_TOO_LONG,
NOTE_REQUIRED, RED_FLAG_CHECK_UNAVAILABLE).
"""


class RuleError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or REASON_MESSAGES.get(code, code))
        self.code = code
        self.message = message or REASON_MESSAGES.get(code, code)


REASON_MESSAGES: dict[str, str] = {
    "INVALID_START_TIME": "Start time must be on a 10-minute mark.",
    "IN_PAST": "That time is in the past.",
    "BEYOND_30_DAYS": "Bookings are open up to 30 days ahead.",
    "CLINIC_CLOSED": "The clinic is closed on Sundays.",
    "HOLIDAY": "The clinic is closed on that date.",
    "OUTSIDE_SESSION": (
        "The clinic is closed at that time (lunch 1–2 PM, or before 9 AM / after 6 PM)."
    ),
    "ENDS_AFTER_SESSION": "That appointment would end after the session closes.",
    "DOCTOR_OFF": "That doctor is not at the clinic in that session.",
    "SURGERY_SESSION": "That doctor is operating in that session, not seeing patients.",
    "SPECIALITY_MISMATCH": "That doctor does not cover that speciality.",
    "DOUBLE_BOOKED": "That slot is already booked with the same doctor.",
    "ACTIVE_BOOKING_EXISTS": "You already have an active booking in that speciality.",
    "NO_PREVIOUS_VISIT": "A follow-up needs a previous completed visit in that speciality.",
    "FOLLOW_UP_DIFFERENT_DOCTOR": (
        "A follow-up must be with the doctor who saw you last in that speciality."
    ),
    "INSIDE_2_HOURS": (
        "Cancellation less than 2 hours before the appointment. Please contact Staff."
    ),
    "NOT_YOUR_APPOINTMENT": "That appointment belongs to another patient.",
    "NOT_ACTIVE": "That appointment is already cancelled or completed.",
    # --- Iter 2 ---
    "REASON_REQUIRED": "Please tell us the reason for your visit.",
    "REASON_TOO_LONG": "Reason is too long — please keep it under 300 characters.",
    "NOTE_REQUIRED": "A note is required when marking a visit completed.",
    "RED_FLAG_CHECK_UNAVAILABLE": (
        "We couldn't check your reason just now. "
        "Please try again, or call the clinic if it's urgent."
    ),
}


# Default is 409 Conflict (booking-rule refusals). Codes that correspond to
# request-shape errors return 400; the LLM-infra failure returns 503.
REASON_STATUS: dict[str, int] = {
    "REASON_REQUIRED": 400,
    "REASON_TOO_LONG": 400,
    "NOTE_REQUIRED": 400,
    "RED_FLAG_CHECK_UNAVAILABLE": 503,
    "NOT_YOUR_APPOINTMENT": 403,
}


# A convenience list used by tests to confirm the contract stays at 21 entries.
REASON_CODES: frozenset[str] = frozenset(REASON_MESSAGES.keys())
