"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ApiError, getDoctorSummary } from "@/lib/api";
import { getSession } from "@/lib/session";
import type { DoctorSummary } from "@/lib/types";

const SUMMARY_FALLBACK = "Summary unavailable. See the notes below.";

export default function DoctorPatientPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<DoctorSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const s = getSession();
    if (!s || s.role !== "doctor") {
      router.push("/");
      return;
    }
    getDoctorSummary(id)
      .then(setData)
      .catch((e: ApiError) =>
        setErr(`${e.code ? e.code + ": " : ""}${e.message}`),
      );
  }, [router, id]);

  if (err) {
    return (
      <main className="max-w-3xl mx-auto py-12 px-6">
        <p className="text-clinic-danger text-sm">{err}</p>
        <Link
          href="/doctor"
          className="inline-block mt-4 text-sm text-slate-600 underline"
        >
          Back to schedule
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="max-w-3xl mx-auto py-12 px-6">
        <p className="text-sm text-slate-500">Loading patient…</p>
      </main>
    );
  }

  const summaryIsFallback = data.summary.trim() === SUMMARY_FALLBACK;

  return (
    <main className="max-w-3xl mx-auto py-12 px-6">
      <Link href="/doctor" className="text-sm text-slate-600 underline">
        ← Back to schedule
      </Link>
      <div className="mt-2 flex items-baseline justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-clinic-accent">Patient</p>
          <h1 className="text-2xl font-bold">Patient {id}</h1>
        </div>
      </div>

      <section className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 border border-slate-200 rounded-lg p-4 bg-white">
          <p className="text-xs uppercase tracking-widest text-slate-500">
            AI summary of recorded notes. Check the notes below.
          </p>
          <p
            className={`mt-2 leading-snug whitespace-pre-wrap ${
              summaryIsFallback ? "text-slate-500 italic" : "text-slate-900"
            }`}
          >
            {data.summary}
          </p>
        </div>
        <aside className="border border-slate-200 rounded-lg p-4 bg-slate-50 text-sm">
          <p className="text-xs uppercase tracking-widest text-slate-500">Profile</p>
          <dl className="mt-2 space-y-2">
            <div>
              <dt className="text-slate-500">Year of birth</dt>
              <dd>{data.profile.year_of_birth ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">General health</dt>
              <dd>{data.profile.general_health ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Allergies</dt>
              <dd>{data.profile.allergies ?? "—"}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Past notes</h2>
        {data.past_visits.length === 0 ? (
          <p className="text-sm text-slate-500 mt-2">
            No previous visits on record.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {data.past_visits.map((v, i) => (
              <li
                key={i}
                className="border border-slate-200 rounded-lg p-3 bg-white"
              >
                <div className="text-sm text-slate-600 flex gap-3">
                  <span className="font-mono">{v.date}</span>
                  <span>·</span>
                  <span>{v.doctor_name}</span>
                  <span>·</span>
                  <span>{v.speciality}</span>
                </div>
                <p className="mt-1 text-slate-900 whitespace-pre-wrap">
                  {v.doctor_note || <em className="text-slate-500">No note recorded.</em>}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
