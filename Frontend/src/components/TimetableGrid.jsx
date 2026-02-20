/**
 * TimetableGrid — College period grid
 *
 * Layout matches the reference image:
 *   Rows    : Day (Mon–Sat) grouped, one sub-row per Branch+Year section
 *   Columns : P1 | P2 | BREAK | P3 | P4 | LUNCH | P5 | P6 | P7
 *   Cell    : Subject\nTeacher\nRoom  (LAB badge if is_lab)
 */

import { useMemo } from "react";

// ── Constants ─────────────────────────────────────────────────────────────────
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DAY_SHORT = {
    Monday: "MON", Tuesday: "TUE", Wednesday: "WED",
    Thursday: "THU", Friday: "FRI", Saturday: "SAT"
};

// Periods in display order, with separators
const COL_DEFS = [
    { type: "period", period: 1, label: "8:00–9:00" },
    { type: "period", period: 2, label: "9:00–10:00" },
    { type: "sep", label: "BREAK" },
    { type: "period", period: 3, label: "10:15–11:15" },
    { type: "period", period: 4, label: "11:15–12:15" },
    { type: "sep", label: "LUNCH" },
    { type: "period", period: 5, label: "13:00–14:00" },
    { type: "period", period: 6, label: "14:00–15:00" },
    { type: "period", period: 7, label: "15:15–16:15" },
];

const BRANCH_COLORS = {
    CS: "#6366f1", EC: "#10b981", ME: "#f59e0b",
    CE: "#8b5cf6", EE: "#f97316", IT: "#ec4899",
    CH: "#22c55e", DEFAULT: "#64748b",
};

function branchColor(branch) {
    const key = (branch || "").toUpperCase().slice(0, 2);
    return BRANCH_COLORS[key] || BRANCH_COLORS.DEFAULT;
}

// ── TimetableGrid Component ────────────────────────────────────────────────────
function TimetableGrid({ timetable }) {
    if (!timetable) return null;

    // Build data: { day → { "branch|year" → { period → slot } } }
    const { sections, byDay } = useMemo(() => {
        const raw = timetable.timetable || timetable;
        if (!raw || typeof raw !== "object") return { sections: [], byDay: {} };

        const sectionSet = new Set();
        const byDay = {};

        for (const day of DAYS) {
            const slots = raw[day] || [];
            byDay[day] = {};
            for (const slot of slots) {
                if (!slot || slot.is_free) continue;
                const key = `${slot.branch}|${slot.year || ""}`;
                sectionSet.add(key);
                if (!byDay[day][key]) byDay[day][key] = {};
                byDay[day][key][slot.period] = slot;
            }
        }

        // Sort sections: by branch then year
        const sections = [...sectionSet].sort((a, b) => {
            const [aBr, aYr] = a.split("|");
            const [bBr, bYr] = b.split("|");
            return aBr !== bBr ? aBr.localeCompare(bBr) : (aYr || "").localeCompare(bYr || "");
        });

        return { sections, byDay };
    }, [timetable]);

    if (!sections.length) {
        return (
            <div className="tt-empty">
                No timetable data to display.
            </div>
        );
    }

    const meta = timetable.label || "";
    const branch = timetable.branch || "";
    const year = timetable.year || "";

    return (
        <div className="tt-wrap">
            {/* ── Header ── */}
            <div className="tt-header">
                <div className="tt-title">
                    🎓 SHRI RAM MURTI SMARAK COLLEGE OF ENGINEERING AND TECHNOLOGY
                </div>
                <div className="tt-subtitle">
                    TIME TABLE &nbsp;·&nbsp; B.Tech
                    {branch ? ` · ${branch}` : ""}
                    {year ? ` · Year ${year}` : ""}
                </div>
                {meta && <div className="tt-meta">{meta}</div>}
            </div>

            {/* ── Scrollable table ── */}
            <div className="tt-scroll">
                <table className="tt-table">
                    <thead>
                        <tr>
                            <th className="tt-th tt-day-col">DAY</th>
                            <th className="tt-th tt-sec-col">SECTION</th>
                            {COL_DEFS.map((col, i) =>
                                col.type === "sep" ? (
                                    <th key={i} className="tt-th tt-sep-col">{col.label}</th>
                                ) : (
                                    <th key={i} className="tt-th tt-period-col">
                                        <div className="tt-period-num">P{col.period}</div>
                                        <div className="tt-period-time">{col.label}</div>
                                    </th>
                                )
                            )}
                        </tr>
                    </thead>
                    <tbody>
                        {DAYS.map((day) => {
                            const daySlots = byDay[day] || {};
                            // Only show sections that have at least one slot on this day OR all sections
                            return sections.map((secKey, sIdx) => {
                                const [secBranch, secYear] = secKey.split("|");
                                const color = branchColor(secBranch);
                                const periodMap = daySlots[secKey] || {};
                                const isFirstRow = sIdx === 0;
                                const isLastRow = sIdx === sections.length - 1;

                                return (
                                    <tr key={`${day}-${secKey}`}
                                        className={`tt-row ${isLastRow ? "tt-row-last" : ""}`}>
                                        {/* Day label — only on first section row */}
                                        {isFirstRow && (
                                            <td className="tt-day-cell" rowSpan={sections.length}>
                                                <span className="tt-day-label">{DAY_SHORT[day]}</span>
                                            </td>
                                        )}

                                        {/* Section label */}
                                        <td className="tt-sec-cell">
                                            <span className="tt-branch-dot"
                                                style={{ background: color }} />
                                            <span className="tt-sec-label">
                                                {secBranch}{secYear ? ` Y${secYear}` : ""}
                                            </span>
                                        </td>

                                        {/* Period cells + separators */}
                                        {COL_DEFS.map((col, ci) => {
                                            if (col.type === "sep") {
                                                return (
                                                    <td key={ci} className="tt-sep-cell">
                                                        <span>{col.label}</span>
                                                    </td>
                                                );
                                            }
                                            const slot = periodMap[col.period];
                                            return slot ? (
                                                <td key={ci} className="tt-slot-cell occupied"
                                                    style={{ borderTop: `2px solid ${color}` }}>
                                                    <div className="tt-slot-subject">
                                                        {slot.subject}
                                                        {slot.is_lab && <span className="tt-lab-badge">LAB</span>}
                                                    </div>
                                                    <div className="tt-slot-teacher">{slot.teacher}</div>
                                                    <div className="tt-slot-room">{slot.room}</div>
                                                </td>
                                            ) : (
                                                <td key={ci} className="tt-slot-cell free">
                                                    <span className="tt-free">—</span>
                                                </td>
                                            );
                                        })}
                                    </tr>
                                );
                            });
                        })}
                    </tbody>
                </table>
            </div>

            {/* ── Branch Legend ── */}
            <div className="tt-legend">
                {sections.map((secKey) => {
                    const [br, yr] = secKey.split("|");
                    const c = branchColor(br);
                    return (
                        <span key={secKey} className="tt-legend-chip"
                            style={{ borderColor: c, color: c }}>
                            {br}{yr ? ` Y${yr}` : ""}
                        </span>
                    );
                })}
            </div>
        </div>
    );
}

export default TimetableGrid;
