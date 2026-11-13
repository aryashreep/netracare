"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, cancelAppointment, listMyAppointments } from "@/lib/api";
import { clearSession, getSession } from "@/lib/session";
import type { Appointment } from "@/lib/types";

export default function PatientHome() {
  const router = useRouter();
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    setErr(null);
    try {
      setAppts(await listMyAppointments());
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  useEffect(() => {
    const s = getSession();
    if (!s || s.role !== "patient") {
      router.push("/");
      return;
    }
    refresh();
  }, [router]);

  async function cancel(id: number) {
    setNotice(null);
    try {
      await cancelAppointment(id);
      setNotice("Appointment cancelled.");
      refresh();
    } catch (e) {
      const ae = e as ApiError;
      setNotice(ae.message);
    }
  }

  function signOut() {
    clearSession();
    router.push("/");
  }

  const session = getSession();

  return (
    <main className="max-w-3xl mx-auto py-12 px-6">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-clinic-accent">Patient</p>
          <h1 className="text-2xl font-bold">
            Hello, {session?.name || "patient"}
          </h1>
        </div>
        <button onClick={signOut} className="text-sm text-slate-500 underline">
          Sign out
        </button>
      </div>

      <div className="mt-6">
        <Link
          href="/patient/book"
          className="inline-block bg-clinic-accent text-white px-4 py-2 rounded"
        >
          Book new appointment
        </Link>
      </div>

      <h2 className="text-lg font-semibold mt-10">My appointments</h2>
      {err && <p className="text-clinic-danger text-sm mt-2">{err}</p>}
      {notice && <p className="text-sm mt-2 text-slate-700">{notice}</p>}

      <ul className="mt-4 divide-y divide-slate-200 border border-slate-200 rounded">
        {appts.length === 0 && (
          <li className="px-4 py-6 text-sm text-slate-500">No appointments yet.</li>
        )}
        {appts.map((a) => (
          <li key={a.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium">
                {a.doctor.name} — {a.speciality} ({a.visit_type.replace("_", " ")})
              </div>
              <div className="text-sm text-slate-500">
                {new Date(a.start_ts).toLocaleString()} · {a.status}
              </div>
            </div>
            {a.status === "booked" && (
              <button
                onClick={() => cancel(a.id)}
                className="text-sm text-clinic-danger"
              >
                Cancel
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
