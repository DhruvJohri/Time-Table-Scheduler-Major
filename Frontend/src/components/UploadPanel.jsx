/**
 * UploadPanel — College Timetable Generator
 *
 * 5-step flow:
 *   Step 1: Admin Profile (name, email, college, role, password)
 *   Step 2: Upload Master Data Excel (.xlsx)
 *   Step 3: Upload Assignment Data Excel (.xlsx)
 *   Step 4: Branch + Year selectors
 *   Step 5: Generate button
 *
 * Auth: After registering a new profile the login happens automatically
 * (via useTimetable.registerAdmin). For returning users who already have
 * an admin in state, the token was restored via login when the page loaded
 * — but if the token expired and needs refreshing, the user can use the
 * re-login section that appears when admin is in state but token is stale.
 */

import { useState, useRef } from "react";
import { useToast } from "../context/ToastContext";

const YEARS = ["All Years", "1", "2", "3", "4"];
const BRANCHES = ["All Branches", "CS", "EC", "ME", "CE", "EE", "IT", "CH"];
const ROLES = ["Admin", "Coordinator", "HOD", "Principal"];

function FileDropZone({ label, file, onFile, accept = ".xlsx,.xls", icon = "📊" }) {
    const ref = useRef();
    const handleDrop = (e) => {
        e.preventDefault();
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
    };
    return (
        <div
            className={`drop-zone${file ? " has-file" : ""}`}
            onClick={() => ref.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
        >
            <input type="file" accept={accept} ref={ref}
                style={{ display: "none" }} onChange={(e) => e.target.files[0] && onFile(e.target.files[0])} />
            <span className="drop-icon">{file ? "✅" : icon}</span>
            <span>{file ? file.name : label}</span>
        </div>
    );
}

function UploadPanel({ admin, onRegisterAdmin, onLogin, onUploadAndGenerate, loading }) {
    const { showToast } = useToast();

    /* Admin form — for new profile creation */
    const [adminForm, setAdminForm] = useState({
        name: "", email: "", college_name: "", role: "Admin", password: "",
    });
    const [adminSaved, setAdminSaved] = useState(!!admin);

    /* Login form — for returning users when token expires */
    const [loginForm, setLoginForm] = useState({ email: admin?.email || "", password: "" });
    const [showLoginForm, setShowLoginForm] = useState(false);

    /* File state */
    const [masterFile, setMasterFile] = useState(null);
    const [assignmentFile, setAssignmentFile] = useState(null);
    const [branch, setBranch] = useState("All Branches");
    const [year, setYear] = useState("All Years");

    /* Upload previews */
    const [masterPreview, setMasterPreview] = useState(null);
    const [assignmentPreview, setAssignmentPreview] = useState(null);

    const setAF = (k, v) => setAdminForm((f) => ({ ...f, [k]: v }));
    const setLF = (k, v) => setLoginForm((f) => ({ ...f, [k]: v }));

    // Save new profile (registers AND logs in automatically)
    const handleSaveAdmin = async (e) => {
        e.preventDefault();
        const { name, email, college_name, password } = adminForm;
        if (!name || !email || !college_name || !password) {
            return showToast("Name, Email, College and Password are required.", "error");
        }
        try {
            await onRegisterAdmin(adminForm);
            setAdminSaved(true);
        } catch (err) {
            showToast(err.message, "error");
        }
    };

    // Login returning user to refresh token
    const handleLogin = async (e) => {
        e.preventDefault();
        const { email, password } = loginForm;
        if (!email || !password)
            return showToast("Email and password are required.", "error");
        try {
            await onLogin(email, password);
            setShowLoginForm(false);
            showToast("Logged in successfully.", "success");
        } catch (err) {
            showToast(err.message, "error");
        }
    };

    const handleGenerate = async (e) => {
        e.preventDefault();
        if (!adminSaved && !admin)
            return showToast("Save your admin profile first (Step 1).", "error");
        if (!masterFile)
            return showToast("Upload Master Data Excel (Step 2).", "error");
        if (!assignmentFile)
            return showToast("Upload Assignment Data Excel (Step 3).", "error");
        try {
            const result = await onUploadAndGenerate({
                masterFile, assignmentFile,
                branch: branch === "All Branches" ? undefined : branch,
                year: year === "All Years" ? undefined : year,
            });
            if (result?.masterResult) setMasterPreview(result.masterResult);
            if (result?.assignResult) setAssignmentPreview(result.assignResult);
            showToast("Timetable generated successfully!", "success");
        } catch (err) {
            showToast(err.message, "error");
        }
    };

    const currentAdmin = admin || (adminSaved ? adminForm : null);

    return (
        <div className="panel upload-panel">
            <div className="panel-title">🏫 Timetable Generator</div>

            {/* ── Step 1: Admin Profile ── */}
            <section className="upload-step">
                <div className="step-header">
                    <span className={`step-badge${adminSaved || admin ? " done" : ""}`}>1</span>
                    <span className="step-label">Admin Profile</span>
                    {(adminSaved || admin) && (
                        <button className="step-edit-btn" type="button"
                            onClick={() => { setAdminSaved(false); setShowLoginForm(false); }}>Edit</button>
                    )}
                </div>

                {!(adminSaved || admin) ? (
                    <form className="form" onSubmit={handleSaveAdmin}>
                        <div className="form-row">
                            <label>Name
                                <input value={adminForm.name}
                                    onChange={(e) => setAF("name", e.target.value)}
                                    placeholder="Your full name" required />
                            </label>
                            <label>Email
                                <input type="email" value={adminForm.email}
                                    onChange={(e) => setAF("email", e.target.value)}
                                    placeholder="admin@college.edu" required />
                            </label>
                        </div>
                        <div className="form-row">
                            <label>College Name
                                <input value={adminForm.college_name}
                                    onChange={(e) => setAF("college_name", e.target.value)}
                                    placeholder="XYZ Engineering College" required />
                            </label>
                            <label>Role
                                <select value={adminForm.role}
                                    onChange={(e) => setAF("role", e.target.value)}>
                                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                </select>
                            </label>
                        </div>
                        <div className="form-row">
                            <label style={{ width: "100%" }}>Password
                                <input type="password" value={adminForm.password}
                                    onChange={(e) => setAF("password", e.target.value)}
                                    placeholder="Choose a secure password"
                                    style={{ width: "100%" }}
                                    required />
                            </label>
                        </div>
                        <button className="btn-primary full-width" type="submit"
                            disabled={loading}>💾 Save Profile</button>
                    </form>
                ) : (
                    <>
                        <div className="profile-summary">
                            <span className="profile-avatar">
                                {(currentAdmin?.name?.[0] ?? "A").toUpperCase()}
                            </span>
                            <div>
                                <div className="profile-name">{currentAdmin?.name}</div>
                                <div className="profile-meta">
                                    {currentAdmin?.college_name} · {currentAdmin?.role}
                                </div>
                                <div className="profile-email">{currentAdmin?.email}</div>
                            </div>
                        </div>
                        {/* Re-login shortcut for token refresh */}
                        {!showLoginForm ? (
                            <button className="btn-outline small" style={{ marginTop: 6 }}
                                onClick={() => { setLoginForm({ email: currentAdmin?.email || "", password: "" }); setShowLoginForm(true); }}>
                                🔑 Re-login (refresh token)
                            </button>
                        ) : (
                            <form className="form" onSubmit={handleLogin} style={{ marginTop: 6 }}>
                                <div className="form-row">
                                    <label>Email
                                        <input type="email" value={loginForm.email}
                                            onChange={(e) => setLF("email", e.target.value)} required />
                                    </label>
                                    <label>Password
                                        <input type="password" value={loginForm.password}
                                            onChange={(e) => setLF("password", e.target.value)}
                                            placeholder="Your password" required />
                                    </label>
                                </div>
                                <button className="btn-primary full-width" type="submit"
                                    disabled={loading}>🔑 Login</button>
                            </form>
                        )}
                    </>
                )}
            </section>

            {/* ── Step 2: Master Data ── */}
            <section className="upload-step">
                <div className="step-header">
                    <span className={`step-badge${masterFile ? " done" : ""}`}>2</span>
                    <span className="step-label">Master Data</span>
                </div>
                <p className="hint-text">
                    .xlsx columns: <code>TeacherName | SubjectName | Year | Branch | Classroom</code>
                </p>
                <FileDropZone
                    label="Click or drag Master Data (.xlsx)"
                    file={masterFile}
                    onFile={(f) => { setMasterFile(f); setMasterPreview(null); }}
                    icon="👩‍🏫"
                />
                {masterPreview && (
                    <div className="preview-chips">
                        <span className="chip">👩‍🏫 {masterPreview.teachers_count} teachers</span>
                        <span className="chip">📚 {masterPreview.subjects_count} subjects</span>
                        <span className="chip">🏛️ {masterPreview.classrooms_count} classrooms</span>
                    </div>
                )}
            </section>

            {/* ── Step 3: Assignment Data ── */}
            <section className="upload-step">
                <div className="step-header">
                    <span className={`step-badge${assignmentFile ? " done" : ""}`}>3</span>
                    <span className="step-label">Assignment Data</span>
                </div>
                <p className="hint-text">
                    .xlsx columns: <code>TeacherName | SubjectName | Year | Branch | LecturesPerWeek</code>
                </p>
                <FileDropZone
                    label="Click or drag Assignment Data (.xlsx)"
                    file={assignmentFile}
                    onFile={(f) => { setAssignmentFile(f); setAssignmentPreview(null); }}
                    icon="📋"
                />
                {assignmentPreview && (
                    <div className="preview-chips">
                        <span className="chip">📋 {assignmentPreview.rows_parsed} assignments</span>
                    </div>
                )}
            </section>

            {/* ── Step 4: Branch + Year ── */}
            <section className="upload-step">
                <div className="step-header">
                    <span className="step-badge">4</span>
                    <span className="step-label">Branch &amp; Year</span>
                </div>
                <div className="form-row">
                    <label>Branch
                        <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                            {BRANCHES.map((b) => <option key={b} value={b}>{b}</option>)}
                        </select>
                    </label>
                    <label>Year
                        <select value={year} onChange={(e) => setYear(e.target.value)}>
                            {YEARS.map((y) => (
                                <option key={y} value={y}>
                                    {y === "All Years" ? "All Years" : `Year ${y}`}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
            </section>

            {/* ── Step 5: Generate ── */}
            <section className="upload-step">
                <div className="step-header">
                    <span className="step-badge">5</span>
                    <span className="step-label">Generate</span>
                </div>
                <button
                    className="btn-primary full-width generate-btn"
                    onClick={handleGenerate}
                    disabled={loading}
                >
                    {loading ? (
                        <><span className="spinner" /> Generating…</>
                    ) : (
                        "🚀 Generate Timetable"
                    )}
                </button>
            </section>
        </div>
    );
}

export default UploadPanel;
