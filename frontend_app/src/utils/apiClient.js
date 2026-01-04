const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, { status, data } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export const ACCESS_TOKEN_KEY = "access_token";
export const REFRESH_TOKEN_KEY = "refresh_token";
export const ADMIN_ACCESS_TOKEN_KEY = "admin_access_token";

export function getStoredToken(key = ACCESS_TOKEN_KEY) {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(key) || "";
}

export function setStoredToken(token, key = ACCESS_TOKEN_KEY) {
  if (typeof window === "undefined") return;
  if (!token) {
    window.localStorage.removeItem(key);
    return;
  }
  window.localStorage.setItem(key, token);
}

export function clearStoredToken(key = ACCESS_TOKEN_KEY) {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(key);
}

function buildUrl(path, query) {
  const base = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
  if (!query || typeof query !== "object") return base;

  const url = new URL(base, API_BASE_URL);
  Object.entries(query).forEach(([k, v]) => {
    if (v == null || v === "") return;
    if (Array.isArray(v)) v.forEach(val => url.searchParams.append(k, val));
    else url.searchParams.set(k, v);
  });
  return url.toString();
}

function isFormData(body) {
  return typeof FormData !== "undefined" && body instanceof FormData;
}

export async function apiFetch(path, {
  method = "GET",
  body,
  headers = {},
  query,
  useAuth = true,
  tokenKey = ACCESS_TOKEN_KEY,
  credentials = "include",
  expectJson = true,
  signal,
} = {}) {
  const finalHeaders = new Headers(headers);
  const form = isFormData(body);
  if (!form && body != null && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  if (useAuth) {
    const token = getStoredToken(tokenKey);
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let payload = undefined;
  if (body != null) {
    if (form) payload = body;
    else if (typeof body === "string") payload = body;
    else payload = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers: finalHeaders,
    body: payload,
    credentials,
    signal,
  });

  const contentType = response.headers.get("content-type") || "";
  let data = null;

  if (response.status !== 204 && response.status !== 205) {
    if (expectJson && contentType.includes("application/json")) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    } else if (expectJson) {
      try {
        data = await response.text();
      } catch {
        data = null;
      }
    }
  }

  if (!response.ok) {
    if (response.status === 401 && useAuth) {
      clearStoredToken(tokenKey);
      clearStoredToken(REFRESH_TOKEN_KEY);
    }
    throw new ApiError(response.statusText || `HTTP ${response.status}`, {
      status: response.status,
      data,
    });
  }

  return data;
}

export async function uploadFiles(path, files, {
  fieldName = "files",
  extraFields,
  useAuth = true,
  tokenKey = ACCESS_TOKEN_KEY,
  headers = {},
  signal,
} = {}) {
  const formData = new FormData();
  if (Array.isArray(files)) {
    files.forEach(file => {
      if (file != null) formData.append(fieldName, file);
    });
  } else if (files) {
    formData.append(fieldName, files);
  }
  if (extraFields && typeof extraFields === "object") {
    Object.entries(extraFields).forEach(([k, v]) => {
      if (Array.isArray(v)) v.forEach(val => formData.append(k, val));
      else if (v != null) formData.append(k, v);
    });
  }

  return apiFetch(path, {
    method: "POST",
    body: formData,
    useAuth,
    tokenKey,
    headers,
    expectJson: true,
    signal,
  });
}

export function parseApiError(err, fallback = "요청 처리 중 오류가 발생했어요.") {
  if (!err) return fallback;
  const data = err instanceof ApiError ? err.data : err;
  if (typeof data === "string") return data;
  if (data && typeof data === "object") {
    if (typeof data.message === "string") return data.message;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map(d => {
          if (!d) return "";
          const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : d.field || d.name;
          const msg = d.msg || d.message || "";
          return field ? `${field}: ${msg}` : msg;
        })
        .filter(Boolean)
        .join("\n");
    }
  }
  if (err instanceof ApiError && typeof err.message === "string" && err.message) {
    return err.message;
  }
  try {
    return JSON.stringify(data);
  } catch {
    return fallback;
  }
}

export function toCurrency(value, unit = "원") {
  if (value == null || value === "") return "협의";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return `${num.toLocaleString()}${unit}`;
}

export const JobsAPI = {
  list: (params) => apiFetch("/api/v1/jobs", { query: params }),
  detail: (id) => apiFetch(`/api/v1/jobs/${id}`),
  applicants: (id, params) => apiFetch(`/api/v1/jobs/${id}/applicants`, { query: params }),
  create: (payload) => apiFetch("/api/v1/jobs", { method: "POST", body: payload }),
  createFromAi: (fields) => apiFetch("/api/v1/jobs/from-image", { method: "POST", body: { fields } }),
  delete: (id) => apiFetch(`/api/v1/jobs/${id}`, { method: "DELETE" }),
  updateStatus: (id, body) => apiFetch(`/api/v1/jobs/${id}`, { method: "PATCH", body }),
};

export const NotificationsAPI = {
  list: () => apiFetch("/api/v1/notifications"),
  markRead: (id, is_read = true) =>
    apiFetch(`/api/v1/notifications/${id}/read`, {
      method: "POST",
      body: { is_read },
    }),
};

export const ApplicationsAPI = {
  list: (params) => apiFetch("/api/v1/applications", { query: params }),
  apply: (payload) => apiFetch("/api/v1/applications", { method: "POST", body: payload }),
  cancel: (applicationId) =>
    apiFetch(`/api/v1/applications/${applicationId}/cancel`, { method: "POST" }),
};

export const MyJobsAPI = {
  list: (params) => apiFetch("/api/v1/my/jobs", { query: params }),
};

export const MatchesAPI = {
  list: (params) => apiFetch("/api/v1/matches", { query: params }),
};

export const ProfileAPI = {
  summary: () => apiFetch("/profile/summary"),
  updateLocation: (payload) =>
    apiFetch("/api/v1/profile/prefs/location", { method: "PUT", body: payload }),
  updateTime: (payload) =>
    apiFetch("/api/v1/profile/prefs/time", { method: "PUT", body: payload }),
  updateHistory: (payload) =>
    apiFetch("/api/v1/profile/prefs/history", { method: "PUT", body: payload }),
  updateCapability: (payload) =>
    apiFetch("/api/v1/profile/prefs/capability", { method: "PUT", body: payload }),
  updateAccount: (payload) =>
    apiFetch("/api/v1/profile/account", { method: "PUT", body: payload }),
};

export const MediaAPI = {
  uploadImages: (files) => uploadFiles("/uploads/images", files),
  uploadAudio: (file) => uploadFiles("/uploads/audio", file, { fieldName: "file" }),
};

export const AIAPI = {
  parseOcr: (payload) => apiFetch("/ocr/parse", { method: "POST", body: payload }),
  parseAsr: (payload) => apiFetch("/asr/parse", { method: "POST", body: payload }),
  mapHeaders: (payload) => apiFetch("/vlm/headers", { method: "POST", body: payload }),
  validateMapping: (payload) => apiFetch("/mapping/validate", { method: "POST", body: payload }),
  createPostFromVoice: (payload) => apiFetch("/voice/post", { method: "POST", body: payload }),
};

export const UsersAPI = {
  me: () => apiFetch("/api/v1/users/me"),
};

export const AuthAPI = {
  async loginWithPin(phone, pin, { endpoint = "/api/v1/auth/login/pin", tokenKey = ACCESS_TOKEN_KEY } = {}) {
    const payloads = [
      { phone_number: phone, pin },
      { phone, pin },
      { phoneNumber: phone, pin },
      { phone_num: phone, pin },
    ];

    let lastError;
    for (const body of payloads) {
      try {
        const data = await apiFetch(endpoint, { method: "POST", body, useAuth: false });
        if (data?.access_token) setStoredToken(data.access_token, tokenKey);
        if (data?.refresh_token) setStoredToken(data.refresh_token, REFRESH_TOKEN_KEY);
        return data;
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError || new Error("로그인에 실패했습니다.");
  },
};

const apiClient = {
  apiFetch,
  uploadFiles,
  parseApiError,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  JobsAPI,
  ApplicationsAPI,
  MyJobsAPI,
  MatchesAPI,
  ProfileAPI,
  MediaAPI,
  AIAPI,
  UsersAPI,
  AuthAPI,
  toCurrency,
  API_BASE_URL,
};

export default apiClient;
