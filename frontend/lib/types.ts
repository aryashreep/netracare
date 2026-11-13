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

export interface Appointment {
  id: number;
  patient: { id: string; name: string };
  doctor: { id: string; name: string };
  speciality: string;
  visit_type: VisitType;
  start_ts: string;
  end_ts: string;
  status: "booked" | "cancelled" | "completed";
}

export interface Refusal {
  code: string;
  message: string;
}

export interface Session {
  token: string;
  role: Role;
  id: string;
  name?: string;
}
