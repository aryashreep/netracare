import type { RedFlagInfo } from "@/lib/types";

/**
 * Renders the clinic's emergency response for a red-flag reason.
 * The emergency_message text comes from the backend as a constant — the
 * component does not synthesize it, so a prompt regression cannot weaken it.
 */
export default function EmergencyPanel({ info }: { info: RedFlagInfo }) {
  return (
    <div
      role="alert"
      className="mt-4 border-2 border-clinic-danger bg-red-50 text-slate-900 rounded-lg p-4"
    >
      <h2 className="text-lg font-semibold text-clinic-danger">
        Urgent — please read
      </h2>
      <p className="mt-2 font-medium leading-snug">{info.emergency_message}</p>
      <p className="mt-3 text-xs uppercase tracking-widest text-clinic-danger">
        {info.category.replace(/_/g, " ")}
      </p>
    </div>
  );
}
