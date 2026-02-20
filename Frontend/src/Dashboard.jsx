/**
 * Dashboard — college timetable single-page orchestrator.
 *
 * Layout:
 *   Topbar  : brand + "Add Profile" button
 *   Sidebar : UploadPanel → HistoryPanel → ExportPanel
 *   Main    : TimetableGrid + states
 */

import { useCallback, useState } from "react";
import useTimetable from "./hooks/useTimetable";
import UploadPanel from "./components/UploadPanel";
import TimetableGrid from "./components/TimetableGrid";
import HistoryPanel from "./components/HistoryPanel";
import ExportPanel from "./components/ExportPanel";
import { useToast } from "./context/ToastContext";

// ── Add Profile slide-in form ─────────────────────────────────────────────────
const ROLES = ["Admin", "Coordinator", "HOD", "Principal"];

function AddProfileModal({ onSave, onClose, loading }) {
    const [form, setForm] = useState({ name: "", email: "", college_name: "", role: "Admin" });
    const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-box" onClick={(e) => e.stopPropagation()}>
                <div className="modal-title">➕ Add / Switch Profile</div>
                <div className="form-row">
                    <label>Name <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Full name" required /></label>
                    <label>Email <input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="admin@college.edu" required /></label>
                </div>
                <div className="form-row">
                    <label>College <input value={form.college_name} onChange={(e) => set("college_name", e.target.value)} placeholder="College name" required /></label>
                    <label>Role
                        <select value={form.role} onChange={(e) => set("role", e.target.value)}>
                            {ROLES.map((r) => <option key={r}>{r}</option>)}
                        </select>
                    </label>
                </div>
                <div className="modal-actions">
                    <button className="btn-outline" onClick={onClose}>Cancel</button>
                    <button className="btn-primary" onClick={() => onSave(form)} disabled={loading}>
                        {loading ? "Saving…" : "Save Profile"}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Dashboard ──────────────────────────────────────────────────────────────────
function Dashboard() {
    const { showToast } = useToast();
    const {
        admin, timetable, versions, loading, error,
        registerAdmin,
        uploadMaster, uploadAssignment,
        generateTimetable,
        fetchVersions, loadVersion, deleteVersion,
        logoutAdmin,
        clearError,
    } = useTimetable();

    const [showAddProfile, setShowAddProfile] = useState(false);

    // ── Register admin (from modal or UploadPanel) ───────────────────────────
    const handleRegisterAdmin = useCallback(async (formData) => {
        try {
            const created = await registerAdmin(formData);
            setShowAddProfile(false);
            showToast("Profile saved!", "success");
            return created;
        } catch (err) {
            showToast(err.message, "error");
            throw err;
        }
    }, [registerAdmin, showToast]);

    // ── Combined upload + generate ───────────────────────────────────────────
    const handleUploadAndGenerate = useCallback(async ({ masterFile, assignmentFile, branch, year }) => {
        const currentAdmin = admin;
        if (!currentAdmin) throw new Error("Admin profile not set.");

        // Step 1: upload master data
        const masterResult = await uploadMaster(masterFile, currentAdmin.email);

        // Step 2: upload assignment data (pass email so backend can look up admin)
        const assignResult = await uploadAssignment(assignmentFile, currentAdmin.email);

        // Step 3: generate
        await generateTimetable({
            admin_id: currentAdmin.id || currentAdmin._id,
            branch: branch || undefined,
            year: year || undefined,
        });

        return { masterResult, assignResult };
    }, [admin, uploadMaster, uploadAssignment, generateTimetable]);

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
                    <button
                        className="btn-add-profile"
                        onClick={() => setShowAddProfile(true)}
                    >
                        ➕ {admin ? "Switch Profile" : "Add Profile"}
                    </button>
                    {admin && (
                        <button
                            className="btn-outline small"
                            onClick={logoutAdmin}
                            title="Sign out / clear profile"
                        >
                            Sign out
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
                {/* Sidebar */}
                <aside className="sidebar">
                    <UploadPanel
                        admin={admin}
                        onRegisterAdmin={handleRegisterAdmin}
                        onUploadAndGenerate={handleUploadAndGenerate}
                        loading={loading}
                    />
                    <HistoryPanel
                        admin={admin}
                        versions={versions}
                        loading={loading}
                        onFetchVersions={fetchVersions}
                        onLoadVersion={loadVersion}
                        onDeleteVersion={deleteVersion}
                    />
                    <ExportPanel timetable={timetable} />
                </aside>

                {/* Content */}
                <main className="main-content">
                    {loading && !timetable && (
                        <div className="loading-state">
                            <div className="loading-spinner" />
                            <p>Running OR-Tools CP-SAT solver…</p>
                        </div>
                    )}

                    {!loading && !timetable && (
                        <div className="empty-state">
                            <div className="empty-icon">📅</div>
                            <h2>No timetable generated yet</h2>
                            <p>
                                Upload your Excel files in the sidebar and click<br />
                                <strong>Generate Timetable</strong> to begin.
                            </p>
                        </div>
                    )}

                    {timetable && <TimetableGrid timetable={timetable} />}
                </main>
            </div>

            {/* ── Add Profile modal ── */}
            {showAddProfile && (
                <AddProfileModal
                    onSave={handleRegisterAdmin}
                    onClose={() => setShowAddProfile(false)}
                    loading={loading}
                />
            )}
        </div>
    );
}

export default Dashboard;
