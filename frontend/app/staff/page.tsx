"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, cancelAppointment, listDoctors, listMyAppointments } from "@/lib/api";
import { clearSession, getSession } from "@/lib/session";
import type { Appointment, Doctor } from "@/lib/types";

export default function StaffHome() {
  const router = useRouter();
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [doctorFilter, setDoctorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("booked");
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    try {
      setAppts(await listMyAppointments());
    } catch (e) {
      setNotice((e as Error).message);
    }
  }

  useEffect(() => {
    const s = getSession();
    if (!s || s.role !== "staff") {
      router.push("/");
      return;
    }
    listDoctors().then(setDoctors).catch(() => void 0);
    refresh();
  }, [router]);

  const filtered = useMemo(
    () =>
      appts.filter(
        (a) =>
          (!doctorFilter || a.doctor.id === doctorFilter) &&
          (!statusFilter || a.status === statusFilter),
      ),
    [appts, doctorFilter, statusFilter],
  );

  async function cancel(id: number) {
    setNotice(null);
    try {
      await cancelAppointment(id);
      setNotice(`Appointment ${id} cancelled.`);
      refresh();
    } catch (e) {
      setNotice((e as ApiError).message);
    }
  }

  function signOut() {
    clearSession();
    router.push("/");
  }

  return (
    <main className="max-w-5xl mx-auto py-12 px-6">
      <div className="flex items-baseline justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-clinic-accent">Staff</p>
          <h1 className="text-2xl font-bold">All appointments</h1>
        </div>
        <button onClick={signOut} className="text-sm text-slate-500 underline">
          Sign out
        </button>
      </div>

      <div className="mt-6 flex gap-4 items-end">
        <Link
          href="/staff/book"
          className="inline-block bg-clinic-accent text-white px-4 py-2 rounded"
        >
          Book walk-in
        </Link>
        <label className="text-sm">
          <span className="text-slate-600 block">Doctor</span>
          <select
            className="border border-slate-300 rounded px-3 py-1.5 mt-1"
            value={doctorFilter}
            onChange={(e) => setDoctorFilter(e.target.value)}
          >
            <option value="">All</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-slate-600 block">Status</span>
          <select
            className="border border-slate-300 rounded px-3 py-1.5 mt-1"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="booked">Booked</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </label>
      </div>

      {notice && <p className="text-sm mt-3 text-slate-700">{notice}</p>}

      <table className="mt-6 w-full text-sm border border-slate-200 rounded">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            <th className="px-3 py-2">When</th>
            <th className="px-3 py-2">Patient</th>
            <th className="px-3 py-2">Doctor</th>
            <th className="px-3 py-2">Speciality</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 && (
            <tr>
              <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                No appointments match.
              </td>
            </tr>
          )}
          {filtered.map((a) => (
            <tr key={a.id} className="border-t border-slate-100">
              <td className="px-3 py-2">{new Date(a.start_ts).toLocaleString()}</td>
              <td className="px-3 py-2">{a.patient.name}</td>
              <td className="px-3 py-2">{a.doctor.name}</td>
              <td className="px-3 py-2">{a.speciality}</td>
              <td className="px-3 py-2">{a.visit_type.replace("_", " ")}</td>
              <td className="px-3 py-2">{a.status}</td>
              <td className="px-3 py-2 text-right">
                {a.status === "booked" && (
                  <button
                    onClick={() => cancel(a.id)}
                    className="text-clinic-danger"
                  >
                    Cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
