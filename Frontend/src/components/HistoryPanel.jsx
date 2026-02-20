/**
 * HistoryPanel — version history browser for college timetables.
 * Shows version cards filtered by Branch + Year.
 */

import { useState, useEffect } from "react";

const YEARS = ["", "1", "2", "3", "4"];
const BRANCHES = ["", "CS", "EC", "ME", "CE", "EE", "IT", "CH"];

function fmt(dateVal) {
    if (!dateVal) return "";
    try {
        return new Date(dateVal).toLocaleDateString("en-IN", {
            day: "2-digit", month: "short", year: "numeric",
        });
    } catch { return ""; }
}

function HistoryPanel({ admin, versions, loading, onFetchVersions, onLoadVersion, onDeleteVersion }) {
    const [branch, setBranch] = useState("");
    const [year, setYear] = useState("");

    useEffect(() => {
        if (admin?.id) {
            onFetchVersions(admin.id, branch || undefined, year || undefined);
        }
    }, [admin, branch, year]);

    return (
        <div className="panel history-panel">
            <div className="panel-title">🕓 Timetable History</div>

            <div className="history-filters">
                <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                    <option value="">All Branches</option>
                    {BRANCHES.filter(Boolean).map((b) =>
                        <option key={b} value={b}>{b}</option>)}
                </select>
                <select value={year} onChange={(e) => setYear(e.target.value)}>
                    <option value="">All Years</option>
                    {YEARS.filter(Boolean).map((y) =>
                        <option key={y} value={y}>Year {y}</option>)}
                </select>
            </div>

            {loading && <div className="history-loading">Loading…</div>}

            {!loading && versions.length === 0 && (
                <div className="history-empty">No versions yet for this filter.</div>
            )}

            <div className="version-list">
                {versions.map((v) => (
                    <div key={v.id} className="version-card">
                        <div className="version-meta">
                            <span className="version-num">v{v.version}</span>
                            <span className="version-branch">{v.branch} · Year {v.year}</span>
                        </div>
                        <div className="version-date">{fmt(v.created_at)}</div>
                        <div className="version-actions">
                            <button
                                className="btn-outline small version-load-btn"
                                onClick={() => onLoadVersion(v.id)}
                                disabled={loading}
                            >
                                Load
                            </button>
                            <button
                                className="btn-danger small"
                                onClick={() => onDeleteVersion(v.id)}
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
