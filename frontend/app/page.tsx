"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listDoctors, loginDoctor, loginPatient, loginStaff } from "@/lib/api";
import { clearSession, setSession } from "@/lib/session";
import type { Doctor, Role } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [role, setRole] = useState<Role>("patient");
  const [mobile, setMobile] = useState("");
  const [name, setName] = useState("");
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [doctorId, setDoctorId] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    clearSession();
    listDoctors().then(setDoctors).catch(() => void 0);
  }, []);

  async function submit() {
    setErr(null);
    try {
      let s;
      if (role === "patient") {
        if (!mobile || !name) throw new Error("Mobile and name required");
        s = await loginPatient(mobile, name);
      } else if (role === "staff") {
        if (!name) throw new Error("Name required");
        s = await loginStaff(name);
      } else {
        if (!doctorId) throw new Error("Pick a doctor");
        const doc = doctors.find((d) => d.id === doctorId);
        s = await loginDoctor(doctorId, doc?.name || "Doctor");
      }
      setSession(s);
      router.push(`/${role}`);
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <main className="max-w-md mx-auto py-16 px-6">
      <p className="text-xs uppercase tracking-widest text-clinic-accent">NetraCare</p>
      <h1 className="text-3xl font-bold mt-1">Sign in</h1>
      <p className="text-sm text-slate-500 mt-1">
        Fictional clinic. Synthetic data only.
      </p>

      <div className="mt-6 flex gap-2">
        {(["patient", "staff", "doctor"] as Role[]).map((r) => (
          <button
            key={r}
            onClick={() => setRole(r)}
            className={`px-4 py-2 rounded border text-sm capitalize ${
              role === r
                ? "bg-clinic-accent text-white border-clinic-accent"
                : "bg-white text-slate-700 border-slate-200"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {role === "patient" && (
          <>
            <input
              className="w-full border border-slate-300 rounded px-3 py-2"
              placeholder="Mobile (e.g. 9000000001)"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
            />
            <input
              className="w-full border border-slate-300 rounded px-3 py-2"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </>
        )}
        {role === "staff" && (
          <input
            className="w-full border border-slate-300 rounded px-3 py-2"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        {role === "doctor" && (
          <select
            className="w-full border border-slate-300 rounded px-3 py-2"
            value={doctorId}
            onChange={(e) => setDoctorId(e.target.value)}
          >
            <option value="">Pick a doctor…</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={submit}
          className="w-full bg-clinic-accent text-white rounded py-2 font-medium"
        >
          Continue
        </button>
        {err && <p className="text-sm text-clinic-danger">{err}</p>}
      </div>
    </main>
  );
}
