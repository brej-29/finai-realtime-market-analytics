export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
}

// Backend issues a per-visitor `finai_ws` sandbox cookie that must be sent
// cross-origin, so every API call goes through here instead of raw fetch.
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith("/") ? `${getApiBase()}${path}` : path;
  return fetch(url, { ...init, credentials: "include" });
}
