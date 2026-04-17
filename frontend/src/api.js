const BASE = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
  }
}

export async function apiFetch(path, options = {}, getToken) {
  const token = await getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(res.status, data.detail || `Request failed (${res.status})`);
  }

  return data;
}

// Convenience wrappers
export const api = {
  get:    (path, getToken)           => apiFetch(path, { method: 'GET' }, getToken),
  post:   (path, body, getToken)     => apiFetch(path, { method: 'POST',   body: JSON.stringify(body) }, getToken),
  patch:  (path, body, getToken)     => apiFetch(path, { method: 'PATCH',  body: JSON.stringify(body) }, getToken),
  del:    (path, getToken)           => apiFetch(path, { method: 'DELETE' }, getToken),
};
