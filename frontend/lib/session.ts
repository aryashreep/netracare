import type { Session } from "./types";

const KEY = "netracare.session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function setSession(s: Session): void {
  window.localStorage.setItem(KEY, JSON.stringify(s));
}

export function clearSession(): void {
  window.localStorage.removeItem(KEY);
}
