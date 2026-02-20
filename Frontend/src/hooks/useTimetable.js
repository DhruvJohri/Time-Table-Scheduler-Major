/**
 * useTimetable — hook owning all college timetable state and actions.
 * Admin profile and active timetable are persisted to localStorage
 * so they survive page refreshes.
 */

import { useState, useCallback, useEffect } from "react";
import {
    registerAdmin as apiRegisterAdmin,
    getAdmin as apiGetAdmin,
    uploadMasterData as apiUploadMaster,
    uploadAssignmentData as apiUploadAssignment,
    generateTimetable as apiGenerate,
    getTimetable as apiGetTimetable,
    deleteTimetable as apiDeleteTimetable,
    getTimetableVersions as apiGetVersions,
} from "../api/api";

// ── localStorage helpers ───────────────────────────────────────────────────────
const LS_ADMIN = "cts_admin";
const LS_TIMETABLE = "cts_timetable";

const lsGet = (key) => {
    try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
};
const lsSet = (key, val) => {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch { }
};
const lsDel = (key) => { try { localStorage.removeItem(key); } catch { } };

// ── Shared loading/error wrapper ───────────────────────────────────────────────
const wrap = (setLoading, setError) => async (fn) => {
    setLoading(true);
    setError(null);
    try {
        return await fn();
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || "Request failed";
        setError(msg);
        throw new Error(msg);
    } finally {
        setLoading(false);
    }
};

export default function useTimetable() {
    // Restore from localStorage on first render
    const [admin, setAdminState] = useState(() => lsGet(LS_ADMIN));
    const [timetable, setTimetableState] = useState(() => lsGet(LS_TIMETABLE));
    const [versions, setVersions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const run = useCallback(wrap(setLoading, setError), []);
    const clearError = useCallback(() => setError(null), []);

    // ── Persist helpers ───────────────────────────────────────────────────────
    const setAdmin = useCallback((data) => {
        setAdminState(data);
        if (data) lsSet(LS_ADMIN, data); else lsDel(LS_ADMIN);
    }, []);

    const setTimetable = useCallback((data) => {
        setTimetableState(data);
        if (data) lsSet(LS_TIMETABLE, data); else lsDel(LS_TIMETABLE);
    }, []);

    // ── Auto-fetch versions when admin is set ─────────────────────────────────
    useEffect(() => {
        if (admin?.id) {
            apiGetVersions(admin.id)
                .then(({ data }) => setVersions(Array.isArray(data) ? data : []))
                .catch(() => { });
        }
    }, [admin?.id]);

    // ── Admin Profile ─────────────────────────────────────────────────────────
    const registerAdmin = useCallback(async (data) =>
        run(async () => {
            const { data: created } = await apiRegisterAdmin(data);
            setAdmin(created);
            return created;
        }), [run, setAdmin]);

    const loadAdmin = useCallback(async (email) =>
        run(async () => {
            const { data: profile } = await apiGetAdmin(email);
            setAdmin(profile);
            return profile;
        }), [run, setAdmin]);

    const logoutAdmin = useCallback(() => {
        setAdmin(null);
        setTimetable(null);
        setVersions([]);
    }, [setAdmin, setTimetable]);

    // ── Upload Master Data ────────────────────────────────────────────────────
    const uploadMaster = useCallback(async (file, adminEmail) =>
        run(async () => {
            const { data } = await apiUploadMaster(file, adminEmail);
            return data;
        }), [run]);

    // ── Upload Assignment Data ────────────────────────────────────────────────
    const uploadAssignment = useCallback(async (file, adminEmail) =>
        run(async () => {
            const { data } = await apiUploadAssignment(file, adminEmail);
            return data;
        }), [run]);

    // ── Generate ──────────────────────────────────────────────────────────────
    const generateTimetable = useCallback(async (payload) =>
        run(async () => {
            const { data } = await apiGenerate(payload);
            setTimetable(data);
            // Refresh versions after generating
            if (payload.admin_id) {
                const { data: vers } = await apiGetVersions(payload.admin_id);
                setVersions(Array.isArray(vers) ? vers : []);
            }
            return data;
        }), [run, setTimetable]);

    // ── Versions ──────────────────────────────────────────────────────────────
    const fetchVersions = useCallback(async (userId, branch, year) =>
        run(async () => {
            const { data } = await apiGetVersions(userId, branch, year);
            setVersions(Array.isArray(data) ? data : []);
            return data;
        }), [run]);

    // ── Delete a version ──────────────────────────────────────────────────────
    const deleteVersion = useCallback(async (id) =>
        run(async () => {
            await apiDeleteTimetable(id);
            setVersions((prev) => prev.filter((v) => v.id !== id));
            // Clear active timetable if the deleted version was loaded
            setTimetableState((prev) => {
                if (prev?.id === id) { lsDel(LS_TIMETABLE); return null; }
                return prev;
            });
        }), [run]);

    // ── Load a specific version ───────────────────────────────────────────────
    const loadVersion = useCallback(async (id) =>
        run(async () => {
            const { data } = await apiGetTimetable(id);
            setTimetable(data);
            return data;
        }), [run, setTimetable]);

    return {
        admin, timetable, versions, loading, error,
        registerAdmin, loadAdmin, logoutAdmin,
        uploadMaster, uploadAssignment,
        generateTimetable,
        fetchVersions, loadVersion, deleteVersion,
        clearError,
        setAdmin,
    };
}
