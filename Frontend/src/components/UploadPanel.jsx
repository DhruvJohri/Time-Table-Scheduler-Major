/**
 * UploadPanel — College Timetable Generator
 *
 * Guide-compliant 4-step workflow:
 *   Step 1: Save Admin Profile  (name, email, college, role, password)
 *   Step 2: Upload Master Data Excel (.xlsx)
 *            Required columns: TeacherName | SubjectName | Year | Branch | Classroom
 *   Step 3: Upload Assignment Data Excel (.xlsx)
 *            Required columns: TeacherName | SubjectName | Year | Branch | LecturesPerWeek
 *            Optional column : Section (defaults to "A" if absent)
 *   Step 4: Select Branch + Year + Section → Generate Timetable
 */

import { useState, useRef } from "react";
import { useToast } from "../context/ToastContext";

const YEARS = ["All Years", "1", "2", "3", "4"];
const BRANCHES = ["All Branches", "CS", "EC", "ME", "CE", "EE", "IT", "CH"];
const SECTIONS = ["A", "B", "C", "D"];
const ROLES = ["Admin", "Coordinator", "HOD", "Principal"];

// ── Drop / click file picker ───────────────────────────────────────────────────
function FileDropZone({ label, file, onFile, icon = "📊" }) {
    const ref = useRef();
    return (
        <div
            className={`drop-zone${file ? " has-file" : ""}`}
            onClick={() => ref.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
        >
            <input type="file" accept=".xlsx,.xls" ref={ref}
                style={{ display: "none" }}
                onChange={(e) => e.target.files[0] && onFile(e.target.files[0])} />
            <span className="drop-icon">{file ? "✅" : icon}</span>
            <span>{file ? file.name : label}</span>
        </div>
    );
}

// ── Step badge ─────────────────────────────────────────────────────────────────
function StepBadge({ num, done }) {
    return <span className={`step-badge${done ? " done" : ""}`}>{done ? "✓" : num}</span>;
}

// ── UploadPanel ────────────────────────────────────────────────────────────────
function UploadPanel({ admin, onSaveAdmin, onUploadAndGenerate, loading }) {
    const { showToast } = useToast();

    /* Step 1 — profile form */
    const [profileForm, setProfileForm] = useState({
        name: admin?.name || "",
        email: admin?.email || "",
        college_name: admin?.college_name || "",
        role: admin?.role || "Admin",
        password: "",
    });
    const [profileSaved, setProfileSaved] = useState(!!admin);
    const setF = (k, v) => setProfileForm((f) => ({ ...f, [k]: v }));

    /* Step 2 & 3 — files */
    const [masterFile, setMasterFile] = useState(null);
    const [assignmentFile, setAssignmentFile] = useState(null);

    /* Preview after upload */
    const [masterPreview, setMasterPreview] = useState(null);
    const [assignmentPreview, setAssignmentPreview] = useState(null);

    /* Step 4 — filters (branch + year + section) */
    const [branch, setBranch] = useState("All Branches");
    const [year, setYear] = useState("All Years");
    const [section, setSection] = useState("A");

    // ── Step 1: Save Profile ───────────────────────────────────────────────────
    const handleSaveProfile = async (e) => {
        e.preventDefault();
        const { name, email, college_name, password } = profileForm;
        if (!name || !email || !college_name || !password)
            return showToast("Name, Email, College and Password are required.", "error");
        try {
            await onSaveAdmin(profileForm);
            setProfileSaved(true);
            showToast("Profile saved!", "success");
        } catch (err) {
            showToast(err.message, "error");
        }
    };

    // ── Step 4: Generate (guide §5 workflow) ──────────────────────────────────
    const handleGenerate = async (e) => {
        e.preventDefault();
        if (!profileSaved && !admin)
            return showToast("Save your profile first (Step 1).", "error");
        if (!masterFile)
            return showToast("Upload Master Data Excel first (Step 2).", "error");
        if (!assignmentFile)
            return showToast("Upload Assignment Data Excel first (Step 3).", "error");
        try {
            const result = await onUploadAndGenerate({
                masterFile,
                assignmentFile,
                branch: branch === "All Branches" ? undefined : branch,
                year: year === "All Years" ? undefined : year,
                section: section || "A",
            });
            if (result?.masterResult) setMasterPreview(result.masterResult);
            if (result?.assignResult) setAssignmentPreview(result.assignResult);
            showToast("Timetable generated successfully!", "success");
        } catch (err) {
            showToast(err.message, "error");
        }
    };

    const currentAdmin = admin || (profileSaved ? profileForm : null);

    return (
        <div className="panel upload-panel">
            <div className="panel-title">🏫 Timetable Generator</div>

            {/* ── Step 1: Admin Profile ── */}
            <section className="upload-step">
                <div className="step-header">
                    <StepBadge num={1} done={!!(profileSaved || admin)} />
                    <span className="step-label">Admin Profile</span>
                    {(profileSaved || admin) && (
                        <button className="step-edit-btn" type="button"
                            onClick={() => setProfileSaved(false)}>Edit</button>
                    )}
                </div>

                {!(profileSaved || admin) ? (
                    <form className="form" onSubmit={handleSaveProfile}>
                        <div className="form-row">
                            <label>Name
                                <input value={profileForm.name}
                                    onChange={(e) => setF("name", e.target.value)}
                                    placeholder="Your full name" required />
                            </label>
                            <label>Email
                                <input type="email" value={profileForm.email}
                                    onChange={(e) => setF("email", e.target.value)}
                                    placeholder="admin@college.edu" required />
                            </label>
                        </div>
                        <div className="form-row">
                            <label>College Name
                                <input value={profileForm.college_name}
                                    onChange={(e) => setF("college_name", e.target.value)}
                                    placeholder="XYZ Engineering College" required />
                            </label>
                            <label>Role
                                <select value={profileForm.role}
                                    onChange={(e) => setF("role", e.target.value)}>
                                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                </select>
                            </label>
                        </div>
                        <div className="form-row">
                            <label style={{ width: "100%" }}>Password
                                <input type="password" value={profileForm.password}
                                    onChange={(e) => setF("password", e.target.value)}
                                    placeholder="Set a password for this profile"
                                    style={{ width: "100%" }} required />
                            </label>
                        </div>
                        <button className="btn-primary full-width" type="submit"
                            disabled={loading}>💾 Save Profile</button>
                    </form>
                ) : (
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
                )}
            </section>

            {/* ── Step 2: Master Data ── */}
            <section className="upload-step">
                <div className="step-header">
                    <StepBadge num={2} done={!!masterFile} />
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
                        <span className="chip">📄 {masterPreview.rows_parsed} rows</span>
                    </div>
                )}
            </section>

            {/* ── Step 3: Assignment Data ── */}
            <section className="upload-step">
                <div className="step-header">
                    <StepBadge num={3} done={!!assignmentFile} />
                    <span className="step-label">Assignment Data</span>
                </div>
                <p className="hint-text">
                    .xlsx columns: <code>TeacherName | SubjectName | Year | Branch | LecturesPerWeek</code><br />
                    <span className="hint-optional">Optional: <code>Section</code> column (defaults to A)</span>
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

            {/* ── Step 4: Branch + Year + Section → Generate ── */}
            <section className="upload-step">
                <div className="step-header">
                    <StepBadge num={4} done={false} />
                    <span className="step-label">Filter &amp; Generate</span>
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
                    <label>Section
                        <select value={section} onChange={(e) => setSection(e.target.value)}>
                            {SECTIONS.map((s) => (
                                <option key={s} value={s}>Sec {s}</option>
                            ))}
                        </select>
                    </label>
                </div>
                <button
                    className="btn-primary full-width generate-btn"
                    onClick={handleGenerate}
                    disabled={loading}
                >
                    {loading ? <><span className="spinner" /> Generating…</> : "🚀 Generate Timetable"}
                </button>
            </section>
        </div>
    );
}

export default UploadPanel;
