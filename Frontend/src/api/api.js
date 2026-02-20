/**
 * api.js — Centralised Axios API layer for the College Timetable Generator.
 * Base URL: VITE_API_URL env var (default http://localhost:8000)
 */

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 60000,   // 60s — solver can take time
    headers: { "Content-Type": "application/json" },
});

// ── Admin Profile ──────────────────────────────────────────────────────────────
export const registerAdmin = (data) =>
    api.post("/api/profiles", data);

export const getAdmin = (email) =>
    api.get(`/api/profiles/${encodeURIComponent(email)}`);

export const updateAdmin = (email, data) =>
    api.put(`/api/profiles/${encodeURIComponent(email)}`, data);

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

export const getUserTimetables = (userId, branch, year) => {
    const params = new URLSearchParams();
    if (branch) params.append("branch", branch);
    if (year) params.append("year", year);
    return api.get(`/api/timetables/user/${userId}?${params.toString()}`);
};

export const getTimetableVersions = (userId, branch, year) => {
    const params = new URLSearchParams();
    if (branch) params.append("branch", branch);
    if (year) params.append("year", year);
    return api.get(`/api/timetables/user/${userId}/versions?${params.toString()}`);
};

export const deleteTimetable = (id) =>
    api.delete(`/api/timetables/${id}`);

// ── Export ─────────────────────────────────────────────────────────────────────
export const downloadExport = async (timetableId, format) => {
    const res = await api.get(`/api/export/${timetableId}/${format}`, {
        responseType: "blob",
    });
    const url = URL.createObjectURL(res.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = `timetable_${timetableId}.${format}`;
    link.click();
    URL.revokeObjectURL(url);
};

export const getExportJson = (timetableId) =>
    api.get(`/api/export/${timetableId}/json`);

export default api;
