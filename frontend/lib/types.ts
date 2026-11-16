// Mirror of backend/app/schemas.py DTOs.

export type Role = "patient" | "staff" | "doctor";

export type VisitType = "new" | "follow_up";

export interface Doctor {
  id: string;
  name: string;
  specialities: string[];
}

export interface SlotsResponse {
  doctor_id: string;
  date: string;
  visit_type: VisitType;
  slots: string[]; // ISO datetimes
}

export interface RedFlagInfo {
  category: string;
  why: string;
  emergency_message: string;
}

export interface Appointment {
  id: number;
  patient: { id: string; name: string };
  doctor: { id: string; name: string };
  speciality: string;
  visit_type: VisitType;
  start_ts: string;
  end_ts: string;
  status: "booked" | "cancelled" | "completed";
  // Iter 2 additions, role-scoped on the server.
  reason?: string | null;
  doctor_note?: string | null;
  urgent?: boolean;
  red_flag?: RedFlagInfo | null;
}

export interface Refusal {
  code: string;
  message: string;
  red_flag?: RedFlagInfo;
}

export interface Session {
  token: string;
  role: Role;
  id: string;
  name?: string;
}

// Iter 2: Fact of the Day
export interface FactResponse {
  fact: string;
  caveat: string;
}

// Iter 2: Urgent cases
export interface UrgentCase {
  id: number;
  patient: { id: string; name: string };
  appointment_id: number | null;
  reason_text: string;
  category: string;
  why: string;
  created_at: string;
  seen_at: string | null;
}

// Iter 2: Doctor summary
export interface PastVisit {
  date: string;
  doctor_name: string;
  speciality: string;
  doctor_note: string;
}

export interface Profile {
  year_of_birth: number | null;
  general_health: string | null;
  allergies: string | null;
}

export interface DoctorSummary {
  summary: string;
  past_visits: PastVisit[];
  profile: Profile;
}
