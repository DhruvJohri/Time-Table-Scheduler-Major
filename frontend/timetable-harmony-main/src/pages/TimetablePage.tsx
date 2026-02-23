import React, { useEffect } from "react";
import { useTimetable } from "@/hooks/useTimetable";
import TimetableGrid from "@/components/TimetableGrid";
import { Button } from "@/components/ui/button";
import { RefreshCw, Loader2 } from "lucide-react";

interface Props {
  branch: string;
  year: number;
  section: string;
}

const TimetablePage: React.FC<Props> = ({ branch, year, section }) => {
  const { entries, loading, fetchSection } = useTimetable();

  useEffect(() => {
    fetchSection(branch, year, section);
  }, [branch, year, section]);

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Timetable</h2>
          <p className="text-sm text-muted-foreground">
            {branch} — Year {year} — Section {section}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchSection(branch, year, section)}
          disabled={loading}
        >
          {loading ? <Loader2 className="mr-2 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-2 h-3 w-3" />}
          Refresh
        </Button>
      </div>
      <TimetableGrid entries={entries} loading={loading} />
    </div>
  );
};

export default TimetablePage;
