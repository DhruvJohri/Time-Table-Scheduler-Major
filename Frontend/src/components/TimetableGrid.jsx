/**
 * TimetableGrid.jsx — Guide-compliant flat-array renderer
 *
 * Consumes a flat array of slot objects from GET /timetable/{branch}/{year}/{section}
 * Each slot: { day, period, branch, year(int), section, subject, faculty, room, type }
 *
 * Renders: Mon–Sat rows × P1–P7 columns
 * Highlights: LAB | TUTORIAL | SEMINAR | CLUB via slot.type
 */

import { useMemo, useState } from "react";

// ── Constants ─────────────────────────────────────────────────────────────────
const DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
];
const PERIODS = [1, 2, 3, 4, 5, 6, 7];
const PERIOD_TIMES = {
    1: "8:00–9:00",
    2: "9:00–10:00",
    3: "10:15–11:15",
    4: "11:15–12:15",
    5: "1:00–2:00",
    6: "2:00–3:00",
    7: "3:15–4:15",
};
const BREAK_AFTER = new Set([2, 4]);  // break after P2 and P4

const TYPE_BADGE_CLASS = {
    LAB: "badge-lab",
    TUTORIAL: "badge-tutorial",
    SEMINAR: "badge-seminar",
    CLUB: "badge-club",
};

// Guide §4: derive type from slot.type field (authoritative)
function deriveType(slot) {
    if (slot?.type) return slot.type.toUpperCase();
    const subj = (slot?.subject || "").toLowerCase();
    if (subj.includes("lab")) return "LAB";
    if (subj.includes("tutorial")) return "TUTORIAL";
    if (subj.includes("seminar")) return "SEMINAR";
    return "LECTURE";
}

// ── Sub-components ────────────────────────────────────────────────────────────
function TypeBadge({ type }) {
    const cls = TYPE_BADGE_CLASS[type] || "";
    if (!cls) return null;
    return <span className={`type-badge ${cls}`}>{type}</span>;
}

function ClubCell() {
    return (
        <div className="slot-cell club-cell">
            <span className="slot-subject">Club Activity</span>
            <TypeBadge type="CLUB" />
        </div>
    );
}

function EmptyCell() {
    return <div className="slot-cell empty-cell">—</div>;
}

function SlotCell({ slot }) {
    if (!slot) return <EmptyCell />;
    const type = deriveType(slot);
    return (
        <div className={`slot-cell ${type !== "LECTURE" ? "highlight-cell" : ""}`}
            title={`${slot.faculty || ""} · ${slot.room || ""}`}>
            <span className="slot-subject">{slot.subject}</span>
            {slot.faculty && <span className="slot-faculty">👤 {slot.faculty}</span>}
            {slot.room && <span className="slot-room">🏛 {slot.room}</span>}
            <TypeBadge type={type} />
        </div>
    );
}

// ── FilterBar ─────────────────────────────────────────────────────────────────
const BRANCH_OPTS = ["All", "CS", "EC", "ME", "CE", "EE", "IT", "CH"];
const YEAR_OPTS = ["All", "1", "2", "3", "4"];
const SECTION_OPTS = ["All", "A", "B", "C", "D"];

function FilterBar({ branch, year, section, setBranch, setYear, setSection }) {
    return (
        <div className="filter-bar">
            <label>
                Branch
                <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                    {BRANCH_OPTS.map((b) => (
                        <option key={b} value={b}>{b === "All" ? "All Branches" : b}</option>
                    ))}
                </select>
            </label>
            <label>
                Year
                <select value={year} onChange={(e) => setYear(e.target.value)}>
                    {YEAR_OPTS.map((y) => (
                        <option key={y} value={y}>{y === "All" ? "All Years" : `Year ${y}`}</option>
                    ))}
                </select>
            </label>
            <label>
                Section
                <select value={section} onChange={(e) => setSection(e.target.value)}>
                    {SECTION_OPTS.map((s) => (
                        <option key={s} value={s}>{s === "All" ? "All Sections" : `Sec ${s}`}</option>
                    ))}
                </select>
            </label>
        </div>
    );
}

// ── TimetableGrid ─────────────────────────────────────────────────────────────
function TimetableGrid({ timetable, partial, onClearPartial }) {
    const [filterBranch, setFilterBranch] = useState("All");
    const [filterYear, setFilterYear] = useState("All");
    const [filterSection, setFilterSection] = useState("All");

    // Normalise input: timetable is always expected to be a flat array of slots
    const rawSlots = useMemo(() => {
        if (Array.isArray(timetable)) return timetable;
        if (Array.isArray(timetable?.timetable)) return timetable.timetable;
        if (timetable?.timetable && typeof timetable.timetable === "object") {
            // Legacy nested day-key format — flatten for backward compat
            return Object.values(timetable.timetable).flat();
        }
        return [];
    }, [timetable]);

    // Apply filters
    const filteredSlots = useMemo(() => {
        return rawSlots.filter((slot) => {
            if (!slot) return false;
            if (filterBranch !== "All" && slot.branch !== filterBranch) return false;
            if (filterYear !== "All" && String(slot.year) !== filterYear) return false;
            if (filterSection !== "All" && slot.section !== filterSection) return false;
            return true;
        });
    }, [rawSlots, filterBranch, filterYear, filterSection]);

    // Group into a lookup map: slotMap[day][period] = slot
    // When multiple sections are shown together, prefer the first match
    const slotMap = useMemo(() => {
        const map = {};
        for (const day of DAYS) {
            map[day] = {};
        }
        for (const slot of filteredSlots) {
            const { day, period } = slot;
            if (!map[day]) continue;
            if (!map[day][period]) map[day][period] = slot;
        }
        return map;
    }, [filteredSlots]);

    const hasData = filteredSlots.length > 0;

    return (
        <div className="timetable-panel">
            {/* ── Partial Schedule Warning ── */}
            {partial && partial.length > 0 && (
                <div className="partial-banner" role="alert">
                    <span>⚡ Some subjects could not be scheduled: </span>
                    <strong>{partial.join(", ")}</strong>
                    <button className="dismiss-btn" onClick={onClearPartial}>✕</button>
                </div>
            )}

            <div className="panel-title">📅 Timetable Grid</div>

            {/* ── Filters ── */}
            <FilterBar
                branch={filterBranch} setBranch={setFilterBranch}
                year={filterYear} setYear={setFilterYear}
                section={filterSection} setSection={setFilterSection}
            />

            {!hasData ? (
                <div className="empty-state">
                    <span className="empty-icon">📋</span>
                    <p>No timetable data. Generate one using the panel on the left.</p>
                </div>
            ) : (
                <div className="grid-scroll-wrapper">
                    <table className="timetable-table">
                        <thead>
                            <tr>
                                <th className="day-col">Day</th>
                                {PERIODS.map((p) => (
                                    <th key={p} className="period-col">
                                        <div>P{p}</div>
                                        <div className="period-time">{PERIOD_TIMES[p]}</div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {DAYS.map((day) => (
                                <tr key={day} className={`day-row ${day === "Thursday" ? "thursday-row" : ""}`}>
                                    <td className="day-label">
                                        <div>{day}</div>
                                        {day === "Thursday" && (
                                            <div className="club-note">Club P1 &amp; P7</div>
                                        )}
                                    </td>
                                    {PERIODS.map((period) => {
                                        // Thursday P1 and P7 are always Club Activity
                                        if (day === "Thursday" && (period === 1 || period === 7)) {
                                            return (
                                                <td key={period} className="period-cell">
                                                    <ClubCell />
                                                    {BREAK_AFTER.has(period) && (
                                                        <div className="break-divider">
                                                            {period === 2 ? "☕ Break" : "🍽 Lunch"}
                                                        </div>
                                                    )}
                                                </td>
                                            );
                                        }
                                        const slot = slotMap[day]?.[period];
                                        return (
                                            <td key={period} className="period-cell">
                                                <SlotCell slot={slot} />
                                                {BREAK_AFTER.has(period) && (
                                                    <div className="break-divider">
                                                        {period === 2 ? "☕ Break" : "🍽 Lunch"}
                                                    </div>
                                                )}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default TimetableGrid;
