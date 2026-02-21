/**
 * HistoryPanel — local timetable generation history browser.
 * Receives history array from useTimetable (local + synced backend versions).
 */

import { useState } from "react";

const YEAR_OPTS = ["", "1", "2", "3", "4"];
const BRANCH_OPTS = ["", "CS", "EC", "ME", "CE", "EE", "IT", "CH"];

function fmt(dateVal) {
    if (!dateVal) return "";
    try {
        return new Date(dateVal).toLocaleDateString("en-IN", {
            day: "2-digit", month: "short", year: "numeric",
        });
    } catch { return ""; }
}

function HistoryPanel({ history = [], loading, onLoadEntry, onDeleteEntry }) {
    const [filterBranch, setFilterBranch] = useState("");
    const [filterYear, setFilterYear] = useState("");

    const filtered = history.filter((entry) => {
        if (filterBranch && entry.branch !== filterBranch) return false;
        if (filterYear && String(entry.year) !== filterYear) return false;
        return true;
    });

    return (
        <div className="panel history-panel">
            <div className="panel-title">🕓 Timetable History</div>

            <div className="history-filters">
                <select value={filterBranch} onChange={(e) => setFilterBranch(e.target.value)}>
                    <option value="">All Branches</option>
                    {BRANCH_OPTS.filter(Boolean).map((b) =>
                        <option key={b} value={b}>{b}</option>)}
                </select>
                <select value={filterYear} onChange={(e) => setFilterYear(e.target.value)}>
                    <option value="">All Years</option>
                    {YEAR_OPTS.filter(Boolean).map((y) =>
                        <option key={y} value={y}>Year {y}</option>)}
                </select>
            </div>

            {loading && <div className="history-loading">Loading…</div>}

            {!loading && filtered.length === 0 && (
                <div className="history-empty">No versions yet. Generate a timetable first.</div>
            )}

            <div className="version-list">
                {filtered.map((entry) => (
                    <div key={entry.id} className="version-card">
                        <div className="version-meta">
                            <span className="version-branch">
                                {entry.branch || "All"} · Year {entry.year || "All"} · Sec {entry.section || "A"}
                            </span>
                        </div>
                        <div className="version-label">{entry.label}</div>
                        <div className="version-date">{fmt(entry.createdAt)}</div>
                        <div className="version-actions">
                            <button
                                className="btn-outline small version-load-btn"
                                onClick={() => onLoadEntry(entry)}
                                disabled={loading}
                            >
                                Load
                            </button>
                            <button
                                className="btn-danger small"
                                onClick={() => onDeleteEntry(entry.id)}
                                disabled={loading}
                                title="Delete this version"
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default HistoryPanel;
