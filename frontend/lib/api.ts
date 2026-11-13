import { getSession } from "./session";
import type {
  Appointment,
  Doctor,
  Refusal,
  Session as SessionT,
  SlotsResponse,
  VisitType,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
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
    throw new ApiError(resp.status, message, r.code);
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
