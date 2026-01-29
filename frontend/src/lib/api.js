const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function buildHeaders(token, contentType = "application/json") {
  const headers = {
    Accept: "application/json"
  };
  if (contentType) {
    headers["Content-Type"] = contentType;
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function request(path, { method = "GET", token, body, contentType } = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: buildHeaders(token, contentType),
    body
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const message = data?.detail || data?.message || res.statusText;
    throw new Error(message);
  }
  return data;
}

export async function register(payload) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function login(payload) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function me(token) {
  return request("/auth/me", { token });
}

export async function uploadFiles(token, files) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  return request("/upload", {
    method: "POST",
    token,
    body: form,
    contentType: null
  });
}

export async function extractDocument(token, documentId) {
  return request(`/documents/${documentId}/extract`, {
    method: "POST",
    token
  });
}

export async function searchDocument(token, documentId, payload) {
  return request(`/documents/${documentId}/search`, {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export async function askQuestion(token, payload) {
  return request("/ask", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
