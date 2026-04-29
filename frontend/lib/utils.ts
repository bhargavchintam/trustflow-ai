import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getOrCreateSessionId(user: string): string {
  if (typeof window === "undefined") return "";
  const key = `trustflow_session_${user}`;
  let sid = window.localStorage.getItem(key);
  if (!sid) {
    sid = crypto.randomUUID();
    window.localStorage.setItem(key, sid);
  }
  return sid;
}

export function resetSessionId(user: string): string {
  if (typeof window === "undefined") return "";
  const key = `trustflow_session_${user}`;
  const sid = crypto.randomUUID();
  window.localStorage.setItem(key, sid);
  return sid;
}
