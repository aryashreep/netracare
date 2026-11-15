"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  createAppointment,
  fetchSlots,
  listDoctors,
} from "@/lib/api";
import { getSession } from "@/lib/session";
import type { Doctor, RedFlagInfo, VisitType } from "@/lib/types";
import EmergencyPanel from "@/components/EmergencyPanel";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export default function BookPage() {
  const router = useRouter();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [doctorId, setDoctorId] = useState("");
  const [speciality, setSpeciality] = useState("");
  const [visitType, setVisitType] = useState<VisitType>("new");
  const [date, setDate] = useState(isoDate(new Date(Date.now() + 24 * 3600 * 1000)));
  const [slots, setSlots] = useState<string[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [redFlag, setRedFlag] = useState<RedFlagInfo | null>(null);

  useEffect(() => {
    const s = getSession();
    if (!s || s.role !== "patient") {
      router.push("/");
      return;
    }
    listDoctors().then(setDoctors).catch(() => void 0);
  }, [router]);

  const selectedDoctor = useMemo(
    () => doctors.find((d) => d.id === doctorId),
    [doctors, doctorId],
  );

  useEffect(() => {
    if (selectedDoctor && !speciality) {
      setSpeciality(selectedDoctor.specialities[0] || "");
    }
  }, [selectedDoctor, speciality]);

  useEffect(() => {
    setSlots([]);
    setChosen(null);
    if (!doctorId || !date || !visitType) return;
    fetchSlots(doctorId, date, visitType)
      .then((r) => setSlots(r.slots))
      .catch((e) => setErr((e as Error).message));
  }, [doctorId, date, visitType]);

  async function book() {
    if (!chosen || !speciality) return;
    setBusy(true);
    setErr(null);
    setRedFlag(null);
    try {
      const appt = await createAppointment({
        doctor_id: doctorId,
        speciality,
        visit_type: visitType,
        start_ts: chosen,
        reason: reason.trim(),
      });
      // Happy path WITH red flag: still booked, but we must show the emergency
      // panel before navigating. Hold the user on this screen; they go back to
      // the home page on their own.
      if (appt.red_flag) {
        setRedFlag(appt.red_flag);
        return;
      }
      router.push("/patient");
    } catch (e) {
      const ae = e as ApiError;
      if (ae.redFlag) setRedFlag(ae.redFlag);
      setErr(`${ae.code ? ae.code + ": " : ""}${ae.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto py-12 px-6">
      <p className="text-xs uppercase tracking-widest text-clinic-accent">Patient</p>
      <h1 className="text-2xl font-bold">Book an appointment</h1>

      <div className="mt-6 space-y-4">
        <label className="block">
          <span className="text-sm text-slate-600">Doctor</span>
          <select
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
            value={doctorId}
            onChange={(e) => {
              setDoctorId(e.target.value);
              setSpeciality("");
            }}
          >
            <option value="">Pick a doctor…</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.specialities.join(", ")})
              </option>
            ))}
          </select>
        </label>

        {selectedDoctor && (
          <label className="block">
            <span className="text-sm text-slate-600">Speciality</span>
            <select
              className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
              value={speciality}
              onChange={(e) => setSpeciality(e.target.value)}
            >
              {selectedDoctor.specialities.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="text-sm text-slate-600">Visit type</span>
          <select
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
            value={visitType}
            onChange={(e) => setVisitType(e.target.value as VisitType)}
          >
            <option value="new">New consultation (20 min)</option>
            <option value="follow_up">Follow-up (10 min)</option>
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-slate-600">Date</span>
          <input
            type="date"
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        {doctorId && (
          <div>
            <span className="text-sm text-slate-600 block mb-2">
              {slots.length
                ? `${slots.length} free slot${slots.length === 1 ? "" : "s"}`
                : "No free slots on this date."}
            </span>
            <div className="flex flex-wrap gap-2">
              {slots.map((s) => (
                <button
                  key={s}
                  onClick={() => setChosen(s)}
                  className={`px-3 py-1 rounded border text-sm ${
                    chosen === s
                      ? "bg-clinic-accent text-white border-clinic-accent"
                      : "bg-white text-slate-700 border-slate-200"
                  }`}
                >
                  {new Date(s).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </button>
              ))}
            </div>
          </div>
        )}

        <label className="block">
          <span className="text-sm text-slate-600">
            What is the reason for your visit?
          </span>
          <textarea
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2 min-h-[72px]"
            value={reason}
            onChange={(e) => setReason(e.target.value.slice(0, 300))}
            maxLength={300}
            placeholder="A short description (e.g. &quot;Blurred vision when reading, worse at night&quot;)"
          />
          <span className="text-xs text-slate-500 block mt-1">
            {reason.length}/300 characters · required
          </span>
        </label>

        {redFlag && <EmergencyPanel info={redFlag} />}

        <button
          onClick={book}
          disabled={!chosen || !reason.trim() || busy}
          className="w-full bg-clinic-accent text-white rounded py-2 font-medium disabled:opacity-50"
        >
          {busy ? "Booking…" : "Confirm booking"}
        </button>

        {err && <p className="text-clinic-danger text-sm">{err}</p>}

        {redFlag && (
          <button
            onClick={() => router.push("/patient")}
            className="w-full border border-slate-300 rounded py-2 font-medium"
          >
            I understand — back to my appointments
          </button>
        )}
      </div>
    </main>
  );
}
