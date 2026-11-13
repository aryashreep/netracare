# Feature Specification: Clinic Booking Foundation

**Feature Branch**: `iteration-1`

**Created**: 2026-11-13

**Status**: Draft

**Input**: Capstone Iteration 1 handout — build the clinic website: three roles, an appointment booking system, and every clinic rule enforced in the backend. No AI features in this feature; it is the foundation that Iterations 2–6 extend.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Patient books an eye appointment (Priority: P1)

A patient (someone who needs an eye exam or follow-up) opens the website, identifies themselves with their mobile number and name, picks a doctor and specialty, chooses a free time, and books. If anything about their choice would break a clinic rule, the booking is refused with a plain-language reason they can act on.

**Why this priority:** This is the core of the whole product. The brief's overall objective is "answer patient questions, route each patient to the right specialist and manage appointments." Without a working, rule-safe booking flow for patients, nothing else in later iterations matters.

**Independent Test:** A tester can act as patient Asha Verma (mobile 9000000001), open the site, see the five doctors, pick a free slot for Dr. Rao for a routine Cataract consultation on a Monday afternoon, book it, and see the booking appear in "my appointments." They can then try each of the 13 refusal scenarios in the Acceptance Scenarios below and confirm each is refused with the stated reason code.

**Acceptance Scenarios:**

1. **Given** a logged-in patient and a free OPD slot for a doctor who covers the chosen specialty, **when** the patient books a new consultation on a 10-minute mark, **then** the system creates a 20-minute booked appointment and shows it under the patient's upcoming appointments.
2. **Given** a slot already booked by another patient, **when** the patient tries to book the same doctor at the same start time, **then** the system refuses with reason code `DOUBLE_BOOKED`.
3. **Given** Dr. Rao's Thursday morning is a surgery session, **when** the patient tries to book Dr. Rao on Thursday between 09:00 and 13:00, **then** the system refuses with reason code `SURGERY_SESSION`.
4. **Given** Dr. Iyer is not at the clinic on Thursdays, **when** the patient tries to book Dr. Iyer any time on a Thursday, **then** the system refuses with reason code `DOCTOR_OFF`.
5. **Given** the clinic is closed on Sundays and on listed holidays, **when** the patient tries to book at 13:30, on a Sunday, or on a date in holidays.csv, **then** the system refuses with reason code `CLINIC_CLOSED`, `OUTSIDE_SESSION`, or `HOLIDAY` as appropriate.
6. **Given** a new consultation needs 20 minutes and the AM session ends at 13:00, **when** the patient tries to start a new consultation at 12:50, **then** the system refuses with reason code `ENDS_AFTER_SESSION`.
7. **Given** bookings are open up to 30 days ahead only, **when** the patient tries to book more than 30 days in the future or any time in the past, **then** the system refuses with reason code `BEYOND_30_DAYS` or `IN_PAST`.
8. **Given** Dr. Khan does not cover Glaucoma, **when** the patient tries to book Dr. Khan for Glaucoma, **then** the system refuses with reason code `SPECIALITY_MISMATCH`.
9. **Given** the patient already has one active (booked) Cataract appointment, **when** they try to book a second Cataract appointment, **then** the system refuses with reason code `ACTIVE_BOOKING_EXISTS`.
10. **Given** the patient has never had a completed visit in a specialty, **when** they try to book a follow-up in that specialty, **then** the system refuses with reason code `NO_PREVIOUS_VISIT`.
11. **Given** the patient's last completed Cataract visit was with Dr. Rao, **when** they try to book a Cataract follow-up with Dr. Iyer, **then** the system refuses with reason code `FOLLOW_UP_DIFFERENT_DOCTOR`.
12. **Given** the appointment starts in less than 2 hours, **when** the patient tries to cancel, **then** the system refuses with reason code `INSIDE_2_HOURS` and tells the patient to contact Staff.
13. **Given** an appointment has been cancelled, **when** another patient looks for slots at that time, **then** the slot is offered and can be booked by anyone.

### User Story 2 — Staff manages every appointment (Priority: P2)

A member of front-desk staff logs in and sees every appointment for every doctor. They can book an appointment for any patient (including a walk-in), cancel any appointment, and in particular cancel a late appointment that a patient could not cancel themselves.

**Why this priority:** Staff are the safety net for the patient flow (P1). The brief's rule "Inside 2 hours, the request goes to staff" cannot be satisfied without Staff capabilities. Staff also unblock walk-ins who cannot self-serve.

**Independent Test:** A tester acts as Staff, books a walk-in appointment for an existing patient who is at the counter, then cancels an appointment that starts in one hour (which a patient would not be allowed to cancel), and verifies both actions succeed and are visible to the right people.

**Acceptance Scenarios:**

1. **Given** a patient is at the counter, **when** Staff selects that patient and books a free OPD slot, **then** the appointment is created and appears in both the Staff view and the patient's view.
2. **Given** an appointment that starts in less than 2 hours, **when** Staff cancels it, **then** the system accepts the cancellation regardless of the time rule, and the slot becomes free again.
3. **Given** Staff viewing the day's bookings, **when** they filter by doctor or date, **then** they see all appointments for that scope, across all patients.

### User Story 3 — Doctor sees their day and marks visits completed (Priority: P3)

A doctor logs in by picking their name, sees their schedule for a chosen day, sees which patient is in each slot, and marks a visit completed after they have seen the patient. Completing a visit is what makes a future follow-up with that same doctor valid.

**Why this priority:** Without a "completed" state, the follow-up rule (Scenario 10 above) cannot be verified, and Iteration 2's doctor note feature has nothing to attach to. However, the actual value for patients and Staff is delivered by P1 and P2; a doctor could temporarily mark visits completed elsewhere.

**Independent Test:** A tester picks Dr. Rao from the doctor login, books a test appointment for Asha Verma for the next morning, then — logged in as Dr. Rao — opens the day's schedule, sees Asha's appointment, and clicks "Mark completed." Asha can then book a Cataract follow-up with Dr. Rao but not with any other doctor.

**Acceptance Scenarios:**

1. **Given** a doctor picks a date, **when** they open their schedule, **then** they see all their booked appointments for that date, with each patient's name and the start time.
2. **Given** an appointment in the past, **when** the doctor clicks "Mark completed," **then** the appointment's status becomes `completed` and the patient can book a follow-up in that specialty with that doctor.
3. **Given** a doctor viewing a patient's row, **when** that patient belongs to another doctor's slot, **then** the second doctor's slot is not shown on this doctor's screen.

### User Story 4 — Simple identification for three roles (Priority: P1)

Each role has a lightweight sign-in: a patient enters their mobile number and name (an unknown mobile creates a new patient); a doctor picks their name; a member of staff enters a name. These three sign-ins return a session the browser uses to make further requests, and every request is checked against the signed-in role server-side.

**Why this priority:** Role-scoped access is what guarantees the brief's non-negotiable "patients only ever see their own appointments and details." It is a P1 because without it, P1 (patient booking) cannot be safely demonstrated — a patient could otherwise read or change another patient's data.

**Independent Test:** A tester signs in as patient A, notes the appointment ID of patient B (visible only to Staff in the Staff view), signs in as patient A again, and asks the booking system directly for patient B's appointment. The system refuses with reason code `NOT_YOUR_APPOINTMENT`.

**Acceptance Scenarios:**

1. **Given** a new mobile number and a name, **when** a person signs in as a patient, **then** a patient record is created and they can book an appointment for themselves.
2. **Given** a signed-in patient, **when** they attempt to read or cancel another patient's appointment, **then** the system refuses with reason code `NOT_YOUR_APPOINTMENT`.
3. **Given** a signed-in doctor, **when** they attempt to read or modify another doctor's schedule, **then** the system refuses.

### Edge Cases

- **Start-time alignment.** If a patient (or an automated client) submits a start time that is not on a 10-minute mark (e.g. 10:07), the system refuses with `INVALID_START_TIME`.
- **Cancel, then rebook.** A cancelled appointment's slot becomes free immediately for any patient to book.
- **Reschedule (optional).** If reschedule is implemented as a stretch goal, it is modeled as "cancel + new booking" — the same 2-hour rule and the full rule check apply.
- **Acting on a non-active appointment.** Cancelling an already-cancelled or already-completed appointment is refused with `NOT_ACTIVE`.
- **Doctor off (future iterations).** Doctor leave is explicitly out of scope for this feature; it is Iteration 4's responsibility.

## Requirements *(mandatory)*

### Functional Requirements

#### Identity & access

- **FR-001:** The system MUST support three roles — Patient, Staff, Doctor — each with a distinct sign-in path. A patient signs in with mobile + name; a doctor signs in by picking their name from the known list; staff signs in with a name.
- **FR-002:** The system MUST enforce role-scoped access to data on every request on the server side. Patients see only their own appointments and details. Doctors see only their own schedule and the patients booked with them. Staff see everything.
- **FR-003:** The system MUST refuse any cross-patient access attempt with reason code `NOT_YOUR_APPOINTMENT`.

#### Data

- **FR-004:** The system MUST load the five doctors, the weekly schedule, the holidays, and the 25 patients from the Iteration-1 data pack when the application starts. Appointments start empty and are created by the app.
- **FR-005:** The system MUST represent an appointment by: a patient, a doctor, a specialty, a visit type (`new` or `follow_up`), a start time, a status (`booked`, `cancelled`, or `completed`), and the role that created it.

#### Clinic hours & calendar

- **FR-006:** The clinic MUST be considered open Monday through Saturday, 09:00–13:00 (AM session) and 14:00–18:00 (PM session). It MUST be considered closed on Sundays and on any date listed in `holidays.csv`.
- **FR-007:** The system MUST refuse any booking that falls outside the session hours (`OUTSIDE_SESSION`), or whose end time would spill past the end of its session (`ENDS_AFTER_SESSION`), on a Sunday (`CLINIC_CLOSED`), or on a holiday (`HOLIDAY`).

#### Slots

- **FR-008:** A new consultation MUST be 20 minutes. A follow-up MUST be 10 minutes. Start times MUST fall on 10-minute marks; any other value is refused with `INVALID_START_TIME`.
- **FR-009:** The system MUST offer only free, bookable OPD slots for a chosen doctor, date, and visit type. A slot in a `SURGERY` session or an `OFF` session MUST NOT be offered and MUST be refused with `SURGERY_SESSION` or `DOCTOR_OFF` if someone tries to book it directly.
- **FR-010:** The system MUST NOT allow two appointments with the same doctor to overlap in time. An attempt to do so is refused with `DOUBLE_BOOKED`.

#### Booking rules

- **FR-011:** Bookings MUST be permitted only within a window starting at "now" and ending 30 days later. Earlier bookings are refused with `IN_PAST`; later ones with `BEYOND_30_DAYS`.
- **FR-012:** A doctor MUST be permitted to see a patient only for a specialty that is in the doctor's list of specialties, otherwise `SPECIALITY_MISMATCH`.
- **FR-013:** A patient MUST NOT hold more than one active (status `booked`) appointment per specialty. A second active booking in the same specialty is refused with `ACTIVE_BOOKING_EXISTS`.
- **FR-014:** A follow-up MUST only be booked with the same doctor who marked the patient's last visit in that specialty as completed. Missing completed visit → `NO_PREVIOUS_VISIT`. Different doctor → `FOLLOW_UP_DIFFERENT_DOCTOR`.

#### Cancellation

- **FR-015:** A patient MUST be permitted to cancel their own appointment only if it starts at least 2 hours from now; otherwise the request is refused with `INSIDE_2_HOURS` and the patient is directed to contact Staff.
- **FR-016:** Staff MUST be permitted to cancel any appointment at any time, including inside the 2-hour window.
- **FR-017:** Cancelling an appointment that is not currently `booked` MUST be refused with `NOT_ACTIVE`.
- **FR-018:** A cancelled appointment's slot MUST immediately become available for a new booking by any patient.

#### Doctor flow

- **FR-019:** A doctor MUST be able to see their own schedule for a chosen date, with each slot's patient and start time.
- **FR-020:** A doctor MUST be able to mark one of their appointments as `completed`. Only the doctor assigned to the appointment is permitted to do so.

#### Refusal contract

- **FR-021:** Every refusal MUST carry one of the 17 canonical `reason_code` values listed in `docs/conventions.md` §2 and a plain-language human-readable message for the UI. The reason codes are a public contract: downstream iterations (LLM agent in Iter 4, MCP server in Iter 6) rely on them being stable.

### Key Entities

- **Doctor** — one of five clinic doctors, each identified by a name and a set of specialties.
- **Weekly schedule entry** — for each doctor, weekday, and session (AM/PM), a status of `OPD` (bookable), `SURGERY`, or `OFF`.
- **Holiday** — a date on which the clinic is closed.
- **Patient** — identified by a unique mobile number and a name; a new mobile number creates a new patient on first sign-in.
- **Appointment** — a scheduled visit linking a patient, a doctor, a specialty, a visit type, a start time, and a lifecycle status (`booked` → `cancelled` or `completed`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001:** Zero bookings in a full run of the brief's 13-row verification table (and, as a stretch goal, zero failures across the 38 rows in `stretch/rule_tests.csv` using the fixed clock `CLINIC_NOW = 2026-11-02 10:00`) break a clinic rule. (Brief §09 target.)
- **SC-002:** 100% of cross-patient access attempts (a patient asking to read or modify another patient's appointment, including by calling the API directly) are refused.
- **SC-003:** Every refusal surfaced to the UI carries both a stable `reason_code` and a human-readable message; every `reason_code` returned matches one of the 17 canonical values in `docs/conventions.md`.
- **SC-004:** A first-time tester, following only the `README.md`, can start the application and successfully complete one booking end-to-end in under 10 minutes.
- **SC-005:** A patient can see, book, and cancel their own appointments, and only their own, from the browser.
- **SC-006:** Staff can see every booked appointment and can cancel any appointment at any time.
- **SC-007:** A doctor can see their day, see each patient, and mark visits completed; marking a visit completed is what unlocks a valid follow-up in that specialty with that doctor.

## Assumptions

- **Sign-in is lightweight on purpose.** This is a classroom-grade identification layer (no passwords, no email verification); the brief and the constitution both acknowledge this. A real clinic would need stronger authentication, but that is out of scope.
- **The clinic clock.** Day-to-day usage runs on the real wall clock. The stretch-goal automated-rule-test suite runs with a fixed clock (`CLINIC_NOW=2026-11-02T10:00:00`) to make the 38 rule tests deterministic.
- **The rules engine is a single backend module.** The constitution requires every rule to live in one place in the backend. The frontend displays refusals it receives; it does not itself validate business rules.
- **Doctor leave is out of scope for this feature.** Iteration 4 adds leave handling; this feature only handles the rule set that governs patients' direct bookings.
- **Reschedule is out of scope for this feature.** If offered as a stretch goal, it is modeled as cancel + new booking so the full rule check still runs.
- **The data pack is authoritative.** Doctors, specialties, the weekly OPD schedule, holidays, and the initial 25 patients come from `data/data-pack-01/`. The handout's examples (e.g., Dr. Rao's Thursday AM is surgery) are shorthand for what the CSVs encode.
- **Follow-up semantics.** A follow-up is 10 minutes and must be with the doctor who completed the patient's most recent visit in the same specialty. "Same doctor" means the exact assigned doctor at completion time, not another doctor who shares that specialty.
