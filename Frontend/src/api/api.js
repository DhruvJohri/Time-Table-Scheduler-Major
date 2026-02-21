/**
 * api.js — Centralised Axios API layer for the College Timetable Generator.
 * Base URL: VITE_API_URL env var (default http://localhost:8000)
 *
 * Auth:
 *   - Token is stored in module-level memory (not localStorage) for security.
 *   - All mutating requests automatically send: Authorization: Bearer <token>
 */

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── In-memory token storage ────────────────────────────────────────────────────
let _token = null;

export const setToken  = (t) => { _token = t; };
export const clearToken = () => { _token = null; };
export const getToken  = () => _token;

// ── Axios instance ─────────────────────────────────────────────────────────────
const api = axios.create({
    baseURL: BASE_URL,
    timeout: 60000,   // 60s — solver can take time
    headers: { "Content-Type": "application/json" },
});

// Attach Bearer token on every request if available
api.interceptors.request.use((config) => {
    if (_token) {
        config.headers["Authorization"] = `Bearer ${_token}`;
    }
    return config;
});

// ── Auth ───────────────────────────────────────────────────────────────────────
export const loginAdmin = (email, password) =>
    api.post("/api/auth/login", { email, password });

// ── Admin Profile ──────────────────────────────────────────────────────────────
export const registerAdmin = (data) =>
    api.post("/api/profiles", data);

export const getAdmin = (email) =>
    api.get(`/api/profiles/${encodeURIComponent(email)}`);

// ── Upload: Master Data ────────────────────────────────────────────────────────
export const uploadMasterData = (file, adminEmail) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(
        `/api/upload/master?admin_email=${encodeURIComponent(adminEmail)}`,
        fd,
        { headers: { "Content-Type": "multipart/form-data" } }
    );
};

// ── Upload: Assignment Data ────────────────────────────────────────────────────
export const uploadAssignmentData = (file, adminEmail) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post(
        `/api/upload/assignment?admin_email=${encodeURIComponent(adminEmail)}`,
        fd,
        { headers: { "Content-Type": "multipart/form-data" } }
    );
};

// ── Timetable Generation ───────────────────────────────────────────────────────
export const generateTimetable = (payload) =>
    api.post("/api/timetables/generate", payload);

// ── Timetable Fetch ────────────────────────────────────────────────────────────
export const getTimetable = (id) =>
    api.get(`/api/timetables/${id}`);

export const getTimetableVersions = (userId, branch, year) => {
    const params = new URLSearchParams();
    if (branch) params.append("branch", branch);
    if (year)   params.append("year",   year);
    return api.get(`/api/timetables/user/${userId}/versions?${params.toString()}`);
};

export const deleteTimetable = (id) =>
    api.delete(`/api/timetables/${id}`);

// ── Export — PDF only ──────────────────────────────────────────────────────────
export const downloadPDF = async (timetableId) => {
    const res = await api.get(`/api/export/${timetableId}/pdf`, {
        responseType: "blob",
    });
    const url  = URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href     = url;
    link.download = `timetable_${timetableId}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
};

export default api;
