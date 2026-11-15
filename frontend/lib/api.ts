import { getSession } from "./session";
import type {
  Appointment,
  Doctor,
  DoctorSummary,
  FactResponse,
  RedFlagInfo,
  Refusal,
  Session as SessionT,
  SlotsResponse,
  UrgentCase,
  VisitType,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code?: string;
  // When a booking is refused by the rules AFTER the red-flag chain fired,
  // the server attaches red_flag so the UI still renders the emergency panel.
  redFlag?: RedFlagInfo;
  constructor(
    status: number,
    message: string,
    code?: string,
    redFlag?: RedFlagInfo,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.redFlag = redFlag;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authed = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json");
  if (authed) {
    const s = getSession();
    if (s) headers.set("authorization", `Bearer ${s.token}`);
  }
  const resp = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!resp.ok) {
    let body: Refusal | { detail?: string } = {} as Refusal;
    try {
      body = await resp.json();
    } catch {
      // ignore
    }
    const r = body as Refusal;
    const message =
      r.message || (body as { detail?: string }).detail || resp.statusText;
    throw new ApiError(resp.status, message, r.code, r.red_flag);
  }
  return (await resp.json()) as T;
}

// --- Auth ---

export async function loginPatient(mobile: string, name: string): Promise<SessionT> {
  const body = await request<SessionT>(
    "/login",
    { method: "POST", body: JSON.stringify({ role: "patient", mobile, name }) },
    false,
  );
  return { ...body, name };
}

export async function loginStaff(name: string): Promise<SessionT> {
  const body = await request<SessionT>(
    "/login",
    { method: "POST", body: JSON.stringify({ role: "staff", name }) },
    false,
  );
  return { ...body, name };
}

export async function loginDoctor(doctorId: string, name: string): Promise<SessionT> {
  const body = await request<SessionT>(
    "/login",
    {
      method: "POST",
      body: JSON.stringify({ role: "doctor", doctor_id: doctorId }),
    },
    false,
  );
  return { ...body, name };
}

// --- Data ---

export function listDoctors(): Promise<Doctor[]> {
  return request<Doctor[]>("/doctors", {}, false);
}

export function fetchSlots(
  doctorId: string,
  date: string,
  visitType: VisitType,
): Promise<SlotsResponse> {
  const qs = new URLSearchParams({
    doctor_id: doctorId,
    date,
    visit_type: visitType,
  });
  return request<SlotsResponse>(`/slots?${qs.toString()}`, {}, false);
}

export function createAppointment(
  body: {
    doctor_id: string;
    speciality: string;
    visit_type: VisitType;
    start_ts: string;
    reason: string;
    patient_id?: string;
  },
): Promise<Appointment> {
  return request<Appointment>("/appointments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listMyAppointments(): Promise<Appointment[]> {
  return request<Appointment[]>("/appointments");
}

export function cancelAppointment(id: number): Promise<{ id: number; status: string }> {
  return request<{ id: number; status: string }>(`/appointments/${id}/cancel`, {
    method: "POST",
  });
}

// Iter 2: complete visit with a required note.
export function completeAppointment(
  id: number,
  doctor_note: string,
): Promise<{ id: number; status: string }> {
  return request<{ id: number; status: string }>(
    `/appointments/${id}/complete`,
    {
      method: "POST",
      body: JSON.stringify({ doctor_note }),
    },
  );
}

// Iter 2: Fact of the Day
export function getFactOfTheDay(previous?: string): Promise<FactResponse> {
  const qs = previous ? `?previous=${encodeURIComponent(previous)}` : "";
  return request<FactResponse>(`/fact-of-the-day${qs}`, {}, false);
}

// Iter 2: Urgent cases (staff-only on server)
export function listUrgentCases(
  includeSeen = false,
): Promise<{ cases: UrgentCase[] }> {
  const qs = includeSeen ? "?include_seen=true" : "";
  return request<{ cases: UrgentCase[] }>(`/urgent-cases${qs}`);
}

export function markUrgentSeen(
  id: number,
): Promise<{ id: number; seen_at: string }> {
  return request<{ id: number; seen_at: string }>(
    `/urgent-cases/${id}/seen`,
    { method: "POST" },
  );
}

// Iter 2: Doctor summary (doctor-only on server)
export function getDoctorSummary(patientId: string): Promise<DoctorSummary> {
  return request<DoctorSummary>(`/doctor/patients/${patientId}/summary`);
}
