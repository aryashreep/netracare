"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ApiError,
  completeAppointment,
  listMyAppointments,
} from "@/lib/api";
import { clearSession, getSession } from "@/lib/session";
import type { Appointment, Session as SessionT } from "@/lib/types";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export default function DoctorHome() {
  const router = useRouter();
  const [session, setSessionState] = useState<SessionT | null>(null);
  const [date, setDate] = useState(isoDate(new Date()));
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [completing, setCompleting] = useState<Appointment | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

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

  function openComplete(a: Appointment) {
    setCompleting(a);
    setNote("");
    setNotice(null);
  }

  async function submitComplete() {
    if (!completing || !note.trim()) return;
    setBusy(true);
    try {
      await completeAppointment(completing.id, note.trim());
      setNotice(`Appointment ${completing.id} marked completed.`);
      setCompleting(null);
      refresh();
    } catch (e) {
      const ae = e as ApiError;
      setNotice(`${ae.code ? ae.code + ": " : ""}${ae.message}`);
    } finally {
      setBusy(false);
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
          <h1 className="text-2xl font-bold">{session.name || "Doctor"}&apos;s day</h1>
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
          <li key={a.id} className="px-4 py-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="font-medium flex items-center gap-2">
                {new Date(a.start_ts).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                — {a.patient.name}
                {a.urgent && (
                  <span className="text-xs uppercase tracking-widest bg-red-100 text-clinic-danger border border-clinic-danger rounded px-1.5 py-0.5">
                    Urgent
                  </span>
                )}
              </div>
              <div className="text-sm text-slate-500">
                {a.speciality} · {a.visit_type.replace("_", " ")} · {a.status}
              </div>
              {a.reason && (
                <div className="text-sm text-slate-600 mt-1 italic">
                  &quot;{a.reason}&quot;
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link
                href={`/doctor/patient/${a.patient.id}`}
                className="text-sm text-slate-600 border border-slate-300 rounded px-3 py-1"
              >
                Open
              </Link>
              {a.status === "booked" && (
                <button
                  onClick={() => openComplete(a)}
                  className="text-sm text-clinic-accent border border-clinic-accent rounded px-3 py-1"
                >
                  Mark completed
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {completing && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4"
        >
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-5">
            <h3 className="font-semibold">
              Complete visit with {completing.patient.name}
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              A short clinical note is required. It is visible to you and Staff,
              and feeds future summaries of this patient.
            </p>
            <textarea
              className="mt-3 w-full border border-slate-300 rounded px-3 py-2 min-h-[120px]"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. VA 6/9 OD, 6/12 OS. Nuclear sclerosis grade 2 OS. Review in 3 months."
            />
            <div className="mt-4 flex gap-2 justify-end">
              <button
                onClick={() => setCompleting(null)}
                className="text-sm text-slate-600 border border-slate-300 rounded px-3 py-1.5"
              >
                Cancel
              </button>
              <button
                onClick={submitComplete}
                disabled={!note.trim() || busy}
                className="text-sm bg-clinic-accent text-white rounded px-3 py-1.5 disabled:opacity-50"
              >
                {busy ? "Saving…" : "Save note & complete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
