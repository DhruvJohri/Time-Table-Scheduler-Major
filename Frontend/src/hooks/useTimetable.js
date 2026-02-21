/**
 * useTimetable.js
 *
 * Guide-compliant workflow (§5):
 *   Step 1 → Save Profile
 *   Step 2 → Click Generate
 *   Step 3 → POST /timetable/generate  (returns only status)
 *   Step 4 → GET  /timetable/{branch}/{year}/{section}
 *   Step 5 → setTimetable(flatArray) → grid renders
 */

import { useState, useEffect, useCallback } from "react";
import {
    saveProfile,
    uploadMasterData,
    uploadAssignmentData,
    generateTimetable,
    getTimetableBySection,
    getAllTimetable,
    getTimetableVersions,
    getTimetableById,
    deleteTimetableById,
    clearAllTimetables,
} from "../api/api";

const LS_ADMIN = "timetable_admin";
const LS_HISTORY = "timetable_history";

export function useTimetable() {
    const [admin, setAdmin] = useState(() => {
        try { return JSON.parse(localStorage.getItem(LS_ADMIN)) || null; }
        catch { return null; }
    });
    const [timetable, setTimetable] = useState(null);  // flat array of slots
    const [history, setHistory] = useState(() => {
        try { return JSON.parse(localStorage.getItem(LS_HISTORY)) || []; }
        catch { return []; }
    });
    const [partial, setPartial] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Persist admin to localStorage
    useEffect(() => {
        if (admin) localStorage.setItem(LS_ADMIN, JSON.stringify(admin));
        else localStorage.removeItem(LS_ADMIN);
    }, [admin]);

    // Persist history to localStorage
    useEffect(() => {
        localStorage.setItem(LS_HISTORY, JSON.stringify(history));
    }, [history]);

    // ── Save Admin Profile ────────────────────────────────────────────────────
    const handleSaveAdmin = useCallback(async (profileData) => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await saveProfile(profileData);
            const adminRecord = { ...profileData, id: data.id || data._id };
            setAdmin(adminRecord);
            return adminRecord;
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || "Failed to save profile.";
            setError(msg);
            throw new Error(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Upload + Generate ─────────────────────────────────────────────────────
    /**
     * Full guide §5 workflow:
     *   1. Upload Master Data
     *   2. Upload Assignment Data
     *   3. POST /timetable/generate  → receive {status, message|unallocated}
     *   4. GET  /timetable/{branch}/{year}/{section} → receive flat slot array
     *   5. setTimetable(flatArray)
     */
    const handleUploadAndGenerate = useCallback(async ({
        masterFile,
        assignmentFile,
        branch,
        year,
        section,
    }) => {
        if (!admin?.id) throw new Error("Admin profile required.");
        setLoading(true);
        setError(null);
        setPartial(null);
        console.log("[useTimetable] generate start:", { branch, year, section });

        try {
            // Step 1 — Upload Master Data
            const masterForm = new FormData();
            masterForm.append("file", masterFile);
            const { data: masterResult } = await uploadMasterData(masterForm, admin.email);
            console.log("[useTimetable] master upload ok:", masterResult);

            // Step 2 — Upload Assignment Data
            const assignForm = new FormData();
            assignForm.append("file", assignmentFile);
            const { data: assignResult } = await uploadAssignmentData(assignForm, admin.email);
            console.log("[useTimetable] assignment upload ok:", assignResult);

            // Step 3 — POST /timetable/generate
            // Response now includes: { status, timetable: [...], message|unallocated }
            const payload = {
                admin_id: admin.id,
                ...(branch ? { branch } : {}),
                ...(year ? { year } : {}),
                ...(section ? { section } : {}),
            };
            console.log("[useTimetable] POST /timetable/generate payload:", payload);
            const { data: genResult } = await generateTimetable(payload);
            console.log("[useTimetable] generate response:", genResult);

            // Handle partial scheduling
            const isPartial = genResult?.status === "partial";
            if (isPartial && Array.isArray(genResult?.unallocated)) {
                setPartial(genResult.unallocated);
                console.warn("[useTimetable] Partial schedule. Unallocated:", genResult.unallocated);
            } else {
                setPartial(null);
            }

            // Step 4 — Use timetable from generate response directly.
            // The generate response now includes the flat slot array.
            // Only fall back to GET /timetable if the response has no timetable.
            let flatSlots = [];

            if (Array.isArray(genResult?.timetable) && genResult.timetable.length > 0) {
                // Primary path: use timetable returned directly by generate
                flatSlots = genResult.timetable;
                console.log("[useTimetable] using timetable from generate response, slots:", flatSlots.length);
            } else {
                // Fallback: GET /timetable (all entries, sorted by created_at DESC)
                console.warn("[useTimetable] generate response had no timetable, falling back to GET /timetable");
                try {
                    const { data: allSlots } = await getAllTimetable();
                    flatSlots = Array.isArray(allSlots) ? allSlots : [];
                    console.log("[useTimetable] fallback GET /timetable returned:", flatSlots.length, "slots");
                } catch (fetchErr) {
                    console.error("[useTimetable] fallback GET /timetable also failed:", fetchErr);
                    flatSlots = [];
                }
            }

            // Step 5 — Update React state immediately
            setTimetable(flatSlots.length > 0 ? flatSlots : null);
            console.log("[useTimetable] setTimetable called with", flatSlots.length, "slots");

            // Update local history
            const entry = {
                id: Date.now().toString(),
                label: `${branch || "All"} / Year ${year || "All"} / Sec ${section || "A"}`,
                branch: branch || "",
                year: year || "",
                section: section || "A",
                createdAt: new Date().toISOString(),
                slots: flatSlots,
            };
            setHistory((prev) => [entry, ...prev].slice(0, 20));

            return { masterResult, assignResult, genResult };
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || "Generation failed.";
            console.error("[useTimetable] error:", msg, err);
            setError(msg);
            throw new Error(msg);
        } finally {
            setLoading(false);
        }
    }, [admin]);

    // ── Load timetable from history entry ─────────────────────────────────────
    const loadFromHistory = useCallback(async (entry) => {
        setLoading(true);
        setError(null);
        try {
            // If entry has a Mongo ID, fetch fresh from backend
            if (entry.mongoId) {
                const { data: doc } = await getTimetableById(entry.mongoId);
                const slots = Array.isArray(doc.timetable) ? doc.timetable : [];
                setTimetable(slots);
            } else if (Array.isArray(entry.slots)) {
                // Local history with cached slots
                setTimetable(entry.slots);
            }
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || "Failed to load history.";
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Delete one history entry ───────────────────────────────────────────────
    const deleteHistoryEntry = useCallback(async (entryId) => {
        setHistory((prev) => prev.filter((e) => e.id !== entryId));
        // If it has a Mongo ID, delete from backend too
        const entry = history.find((e) => e.id === entryId);
        if (entry?.mongoId) {
            try { await deleteTimetableById(entry.mongoId); } catch (_) { }
        }
    }, [history]);

    // ── Clear ALL timetables ──────────────────────────────────────────────────
    const clearAllVersions = useCallback(async () => {
        setLoading(true);
        setError(null);
        setTimetable(null);
        setPartial(null);
        setHistory([]);
        try {
            await clearAllTimetables();
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || "Failed to clear.";
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Load Backend History (optional sync) ──────────────────────────────────
    const syncBackendHistory = useCallback(async () => {
        if (!admin?.id) return;
        try {
            const { data: versions } = await getTimetableVersions(admin.id);
            if (!Array.isArray(versions) || versions.length === 0) return;
            const mapped = versions.map((v) => ({
                id: v.id,
                mongoId: v.id,
                label: v.label || `v${v.version}`,
                branch: v.branch,
                year: v.year,
                section: v.section || "A",
                createdAt: v.created_at || "",
            }));
            setHistory(mapped);
        } catch (_) { /* silent */ }
    }, [admin]);

    const clearPartial = useCallback(() => setPartial(null), []);
    const clearError = useCallback(() => setError(null), []);

    return {
        admin,
        timetable,
        history,
        partial,
        loading,
        error,
        handleSaveAdmin,
        handleUploadAndGenerate,
        loadFromHistory,
        deleteHistoryEntry,
        clearAllVersions,
        syncBackendHistory,
        clearPartial,
        clearError,
    };
}
