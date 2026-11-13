"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, listMyAppointments } from "@/lib/api";
import { clearSession, getSession } from "@/lib/session";
import type { Appointment, Session as SessionT } from "@/lib/types";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

async function completeAppointment(id: number, token: string) {
  const resp = await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/appointments/${id}/complete`,
    {
      method: "POST",
      headers: { authorization: `Bearer ${token}` },
    },
  );
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.message || resp.statusText);
  }
  return resp.json();
}

export default function DoctorHome() {
  const router = useRouter();
  const [session, setSessionState] = useState<SessionT | null>(null);
  const [date, setDate] = useState(isoDate(new Date()));
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const s = getSession();
    if (!s || s.role !== "doctor") {
      router.push("/");
      return;
    }
    setSessionState(s);
  }, [router]);

  async function refresh() {
    setErr(null);
    try {
      setAppts(await listMyAppointments());
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  useEffect(() => {
    if (session) refresh();
  }, [session]);

  const forDay = useMemo(
    () => appts.filter((a) => a.start_ts.slice(0, 10) === date),
    [appts, date],
  );

  async function markCompleted(id: number) {
    if (!session) return;
    setNotice(null);
    try {
      await completeAppointment(id, session.token);
      setNotice(`Appointment ${id} marked completed.`);
      refresh();
    } catch (e) {
      setNotice((e as ApiError).message);
    }
  }

  function signOut() {
    clearSession();
    router.push("/");
  }

  if (!session) return null;

  return (
    <main className="max-w-3xl mx-auto py-12 px-6">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-clinic-accent">Doctor</p>
          <h1 className="text-2xl font-bold">{session.name || "Doctor"}'s day</h1>
        </div>
        <button onClick={signOut} className="text-sm text-slate-500 underline">
          Sign out
        </button>
      </div>

      <label className="block mt-6">
        <span className="text-sm text-slate-600">Date</span>
        <input
          type="date"
          className="mt-1 border border-slate-300 rounded px-3 py-2"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </label>

      {err && <p className="text-sm mt-2 text-clinic-danger">{err}</p>}
      {notice && <p className="text-sm mt-2 text-slate-700">{notice}</p>}

      <ul className="mt-6 divide-y divide-slate-200 border border-slate-200 rounded">
        {forDay.length === 0 && (
          <li className="px-4 py-6 text-sm text-slate-500">No appointments this day.</li>
        )}
        {forDay.map((a) => (
          <li key={a.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium">
                {new Date(a.start_ts).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                — {a.patient.name}
              </div>
              <div className="text-sm text-slate-500">
                {a.speciality} · {a.visit_type.replace("_", " ")} · {a.status}
              </div>
            </div>
            {a.status === "booked" && (
              <button
                onClick={() => markCompleted(a.id)}
                className="text-sm text-clinic-accent border border-clinic-accent rounded px-3 py-1"
              >
                Mark completed
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
