/**
 * Dashboard — College Timetable Generator
 *
 * Guide §5 workflow:
 *   1. Save Profile
 *   2. Upload Master Data Excel
 *   3. Upload Assignment Data Excel
 *   4. Click Generate → POST /timetable/generate → GET /timetable/{branch}/{year}/{section}
 *   5. Grid renders automatically
 *
 * Guide §10: Partial banner shown when status === "partial"
 * Guide §9:  Reset button → DELETE /timetable/clear
 */

import { useCallback } from "react";
import { useTimetable } from "./hooks/useTimetable";
import UploadPanel from "./components/UploadPanel";
import TimetableGrid from "./components/TimetableGrid";
import HistoryPanel from "./components/HistoryPanel";
import ExportPanel from "./components/ExportPanel";
import { useToast } from "./context/ToastContext";

function Dashboard() {
    const { showToast } = useToast();
    const {
        admin,
        timetable,
        history,
        loading,
        error,
        partial,
        handleSaveAdmin,
        handleUploadAndGenerate,
        loadFromHistory,
        deleteHistoryEntry,
        clearAllVersions,
        clearError,
        clearPartial,
    } = useTimetable();

    // ── Reset — DELETE /timetable/clear ───────────────────────────────────────
    const handleResetTimetable = useCallback(async () => {
        try {
            await clearAllVersions();
            showToast("All timetables cleared.", "info");
        } catch (err) {
            showToast(err.message, "error");
        }
    }, [clearAllVersions, showToast]);

    return (
        <div className="dashboard">
            {/* ── Topbar ── */}
            <header className="topbar">
                <div className="topbar-brand">
                    <span className="brand-icon">🎓</span>
                    <span className="brand-name">College Timetable Generator</span>
                </div>
                <div className="topbar-right">
                    {admin && (
                        <div className="topbar-user">
                            <span className="user-avatar">
                                {(admin.name?.[0] ?? "A").toUpperCase()}
                            </span>
                            <div className="user-info">
                                <span className="user-name">{admin.name}</span>
                                <span className="user-college">{admin.college_name}</span>
                            </div>
                        </div>
                    )}
                    {timetable && (
                        <button
                            className="btn-outline small"
                            onClick={handleResetTimetable}
                            disabled={loading}
                            title="Delete ALL timetables and reset (guide §9)"
                        >
                            🔄 Reset Timetable
                        </button>
                    )}
                </div>
            </header>

            {/* ── Error banner ── */}
            {error && (
                <div className="error-banner" onClick={clearError} role="alert">
                    ⚠️ {error} <span className="dismiss">click to dismiss</span>
                </div>
            )}

            {/* ── Main layout ── */}
            <div className="dashboard-body">
                <aside className="sidebar">
                    <UploadPanel
                        admin={admin}
                        onSaveAdmin={handleSaveAdmin}
                        onUploadAndGenerate={handleUploadAndGenerate}
                        loading={loading}
                    />
                    <HistoryPanel
                        history={history}
                        loading={loading}
                        onLoadEntry={loadFromHistory}
                        onDeleteEntry={deleteHistoryEntry}
                    />
                    <ExportPanel timetable={timetable} />
                </aside>

                <main className="main-content">
                    {loading && !timetable && (
                        <div className="loading-state">
                            <div className="loading-spinner" />
                            <div>
                                <p>Running OR-Tools CP-SAT solver…</p>
                                <p className="loading-sub">This may take up to 30 seconds</p>
                            </div>
                        </div>
                    )}
                    {!loading && !timetable && (
                        <div className="empty-state">
                            <div className="empty-icon">📅</div>
                            <h2>No timetable generated yet</h2>
                            <p>Follow the steps in the sidebar to get started.</p>
                            <div className="empty-steps">
                                <div className="empty-step">
                                    <span className="empty-step-num">1</span>
                                    <span>Save your admin profile</span>
                                </div>
                                <div className="empty-step">
                                    <span className="empty-step-num">2</span>
                                    <span>Upload Master Data Excel</span>
                                </div>
                                <div className="empty-step">
                                    <span className="empty-step-num">3</span>
                                    <span>Upload Assignment Data Excel</span>
                                </div>
                                <div className="empty-step">
                                    <span className="empty-step-num">4</span>
                                    <span>Choose Branch / Year / Section → Generate</span>
                                </div>
                            </div>
                        </div>
                    )}
                    {timetable && (
                        <TimetableGrid
                            timetable={timetable}
                            partial={partial}
                            onClearPartial={clearPartial}
                        />
                    )}
                </main>
            </div>
        </div>
    );
}

export default Dashboard;
