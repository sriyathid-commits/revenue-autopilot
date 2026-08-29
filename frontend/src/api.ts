import type { AuditEvent, DemoResponse, Evaluation, Incident, IncidentDetail, Metrics } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => http<{ status: string }>("/health"),
  metrics: () => http<Metrics>("/api/metrics"),
  incidents: () => http<{ total: number; items: Incident[] }>("/api/incidents"),
  incident: (id: string) => http<IncidentDetail>(`/api/incidents/${id}`),
  agents: (id: string) => http<IncidentDetail["agent_results"]>(`/api/agents/${id}`),
  audit: (id: string) => http<AuditEvent[]>(`/api/audit/${id}`),
  evaluation: () => http<Evaluation>("/api/evaluation"),
  demoRun: () => http<DemoResponse>("/api/demo/run", { method: "POST" }),
  demoReset: () => http<{ ok: boolean }>("/api/demo/reset", { method: "POST" }),
  recover: (id: string) => http<unknown>(`/api/recovery/${id}`, { method: "POST" }),
};
