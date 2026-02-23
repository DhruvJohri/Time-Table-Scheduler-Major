import React, { useMemo } from "react";
import { TimetableEntry } from "@/api/timetableApi";
import { Loader2 } from "lucide-react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const PERIODS = [1, 2, 3, 4, 5, 6, 7];

const TYPE_COLORS: Record<string, { bg: string; fg: string }> = {
  LECTURE: { bg: "bg-tt-lecture", fg: "text-tt-lecture-fg" },
  LAB: { bg: "bg-tt-lab", fg: "text-tt-lab-fg" },
  TUTORIAL: { bg: "bg-tt-tutorial", fg: "text-tt-tutorial-fg" },
  SEMINAR: { bg: "bg-tt-seminar", fg: "text-tt-seminar-fg" },
  CLUB: { bg: "bg-tt-club", fg: "text-tt-club-fg" },
  BREAK: { bg: "bg-tt-break", fg: "text-tt-break-fg" },
};

interface Props {
  entries: TimetableEntry[];
  loading: boolean;
}

const isSameLabBlock = (a?: TimetableEntry, b?: TimetableEntry) => {
  if (!a || !b) return false;
  return (
    a.type === "LAB" &&
    b.type === "LAB" &&
    a.day === b.day &&
    a.subject_code === b.subject_code &&
    a.faculty === b.faculty &&
    a.room === b.room
  );
};

const TimetableGrid: React.FC<Props> = ({ entries, loading }) => {
  // Build a map: day -> period -> entry
  const grid = useMemo(() => {
    const map: Record<string, Record<number, TimetableEntry>> = {};
    for (const e of entries) {
      if (!map[e.day]) map[e.day] = {};
      map[e.day][e.period] = e;
    }
    return map;
  }, [entries]);

  // Track only true second slot of 2-period labs.
  const labSecondPeriods = useMemo(() => {
    const set = new Set<string>();
    const byKey = new Map<string, TimetableEntry>();
    for (const e of entries) {
      byKey.set(`${e.day}-${e.period}`, e);
    }
    for (const e of entries) {
      if (e.type === "LAB") {
        const prev = byKey.get(`${e.day}-${e.period - 1}`);
        if (isSameLabBlock(prev, e)) {
          set.add(`${e.day}-${e.period}`);
        }
      }
    }
    return set;
  }, [entries]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading timetable...</span>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <p className="text-lg font-medium">No timetable generated</p>
        <p className="text-sm mt-1">Select branch, year, and section, then generate.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto animate-fade-in">
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-4">
        {Object.entries(TYPE_COLORS).map(([type, colors]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs">
            <div className={`w-3 h-3 rounded-sm ${colors.bg}`} />
            <span className="text-muted-foreground capitalize">{type.toLowerCase()}</span>
          </div>
        ))}
      </div>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="border border-border bg-muted px-3 py-2 text-left font-semibold text-muted-foreground w-24">
              Day / Period
            </th>
            {PERIODS.map((p) => (
              <th
                key={p}
                className="border border-border bg-muted px-3 py-2 text-center font-semibold text-muted-foreground min-w-[130px]"
              >
                Period {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DAYS.map((day) => (
            <tr key={day}>
              <td className="border border-border bg-muted px-3 py-2 font-semibold text-foreground">
                {day}
              </td>
              {PERIODS.map((period) => {
                const key = `${day}-${period}`;

                // Skip if this is the second period of a lab (merged)
                if (labSecondPeriods.has(key)) return null;

                const entry = grid[day]?.[period];
                if (!entry) {
                  return (
                    <td key={period} className="border border-border px-3 py-2 text-center text-muted-foreground">
                      —
                    </td>
                  );
                }

                const colors = TYPE_COLORS[entry.type] || TYPE_COLORS.LECTURE;
                const nextEntry = grid[day]?.[period + 1];
                const isLabStart = entry.type === "LAB" && isSameLabBlock(entry, nextEntry);

                return (
                  <td
                    key={period}
                    colSpan={isLabStart ? 2 : 1}
                    className={`border border-border px-3 py-2 ${colors.bg} ${colors.fg} rounded-sm`}
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="font-semibold text-xs leading-tight">{entry.subject}</span>
                      <span className="text-[10px] opacity-80">{entry.subject_code}</span>
                      <span className="text-[10px] opacity-80">{entry.faculty}</span>
                      <span className="text-[10px] opacity-80">{entry.room}</span>
                      <span className="text-[10px] font-medium uppercase opacity-70">{entry.type}</span>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TimetableGrid;
