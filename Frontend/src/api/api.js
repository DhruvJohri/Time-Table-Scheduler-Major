/**
 * api.js — All API calls for the College Timetable Generator
 * Guide-compliant routes (no /api prefix on timetable routes, no plural)
 */

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 120000, // 2 minutes for generation
    headers: { "Content-Type": "application/json" },
});

// ── Admin Profiles ────────────────────────────────────────────────────────────
export const saveProfile = (payload) =>
    api.post("/api/profiles", payload);

export const loginProfile = (payload) =>
    api.post("/api/auth/login", payload);

// ── Upload ────────────────────────────────────────────────────────────────────
export const uploadMasterData = (formData, adminEmail) =>
    api.post(`/api/upload/master?admin_email=${encodeURIComponent(adminEmail)}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });

export const uploadAssignmentData = (formData, adminEmail) =>
    api.post(`/api/upload/assignment?admin_email=${encodeURIComponent(adminEmail)}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });

// ── Timetable — Guide §4 Routes ───────────────────────────────────────────────

/**
 * POST /timetable/generate
 * Returns: { status: "success"|"partial", message?: "...", unallocated?: [...] }
 * Does NOT return timetable data — call getTimetableBySection after.
 */
export const generateTimetable = (payload) =>
    api.post("/timetable/generate", payload);

/**
 * GET /timetable
 * Returns flat array of ALL timetable slot entries.
 */
export const getAllTimetable = () =>
    api.get("/timetable");

/**
 * GET /timetable/{branch}/{year}/{section}
 * Returns flat array of slots for the most recent matching timetable.
 */
export const getTimetableBySection = (branch, year, section) =>
    api.get(
        `/timetable/${encodeURIComponent(branch)}/${encodeURIComponent(year)}/${encodeURIComponent(section)}`
    );

/**
 * DELETE /timetable/clear
 * Deletes ALL timetables.
 */
export const clearAllTimetables = () =>
    api.delete("/timetable/clear");

// ── Version History (History Panel) ──────────────────────────────────────────
export const getTimetableVersions = (adminId) =>
    api.get(`/timetable/versions/${adminId}`);

export const getTimetableById = (timetableId) =>
    api.get(`/timetable/id/${timetableId}`);

export const deleteTimetableById = (timetableId) =>
    api.delete(`/timetable/id/${timetableId}`);

// ── Export ────────────────────────────────────────────────────────────────────
export const exportTimetable = (adminId, format = "pdf") =>
    api.post(`/api/export/${adminId}`, { format }, {
        responseType: format === "json" ? "json" : "blob",
    });

/**
 * downloadPDF(timetableId) — used by ExportPanel to trigger PDF download.
 */
export const downloadPDF = async (timetableId) => {
    const response = await api.get(`/api/export/${timetableId}/pdf`, {
        responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `timetable_${timetableId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};

export default api;
