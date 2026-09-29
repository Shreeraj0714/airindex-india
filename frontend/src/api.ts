const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export { API_BASE };
